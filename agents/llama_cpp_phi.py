"""Phi ``Model`` implementation backed by ``llama_cpp.Llama`` (local GGUF).

Subclasses ``phi.model.ollama.chat.Ollama`` so ``response`` / ``response_stream``,
tool execution, and metrics handling stay aligned with the Ollama integration, while
``invoke`` / ``invoke_stream`` call ``llama_cpp`` instead of the Ollama HTTP API.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, cast

from pydantic import Field

from phi.model.message import Message
from phi.model.ollama.chat import Ollama

try:
    from llama_cpp import Llama
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "llama-cpp-python is required for LlamaCppChat. Install with: pip install llama-cpp-python"
    ) from exc

_LLAMA_CACHE: dict[tuple[str, int, Optional[int], bool], Llama] = {}


def resolve_gguf_path(
    *,
    model_path: Optional[str] = None,
    model_id: Optional[str] = None,
    env_var: str = "LLAMA_MODEL_PATH",
) -> str:
    """Resolve a filesystem path to a GGUF model.

    Order: explicit ``model_path``, ``LLAMA_MODEL_PATH`` (or *env_var*), then
    ``model_id`` if it looks like a path (contains ``/``, ends with ``.gguf``, etc.).
    """
    raw = (model_path or os.environ.get(env_var) or "").strip()
    if raw:
        p = Path(raw).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"GGUF model not found: {p.resolve()}")
        return str(p.resolve())

    legacy = (model_id or "").strip()
    if legacy.endswith(".gguf") or "/" in legacy or legacy.startswith("~/") or legacy.startswith("./"):
        p = Path(legacy).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"GGUF model not found: {p.resolve()}")
        return str(p.resolve())

    raise ValueError(
        f"No local GGUF path: set environment variable {env_var} or pass model_path=... "
        "(path to a .gguf file). A plain model name like 'llama3.2' is not valid for llama-cpp-python."
    )


class LlamaCppChat(Ollama):
    """Chat model using llama-cpp-python; drop-in replacement for ``Ollama`` in phi agents."""

    name: str = "LlamaCpp"
    provider: str = "LlamaCpp"

    gguf_path: str = Field(..., description="Absolute or user-expandable path to the GGUF weights file.")
    n_ctx: int = Field(default=8192, description="Context size passed to llama_cpp.Llama.")
    n_threads: Optional[int] = Field(default=None, description="Thread count for llama_cpp.Llama.")
    llama_verbose: bool = Field(default=False, description="Verbose flag for llama_cpp.Llama.")
    chat_temperature: float = Field(default=0.2, description="Sampling temperature for chat completion.")

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        resolved = str(Path(self.gguf_path).expanduser().resolve())
        if not Path(resolved).is_file():
            raise FileNotFoundError(f"GGUF model not found: {resolved}")
        object.__setattr__(self, "gguf_path", resolved)

    def _llama_key(self) -> tuple[str, int, Optional[int], bool]:
        return (self.gguf_path, self.n_ctx, self.n_threads, self.llama_verbose)

    def _get_llama(self) -> Llama:
        key = self._llama_key()
        if key not in _LLAMA_CACHE:
            _LLAMA_CACHE[key] = Llama(
                model_path=self.gguf_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=self.llama_verbose,
            )
        return _LLAMA_CACHE[key]

    def get_client(self) -> Any:  # type: ignore[override]
        raise RuntimeError("LlamaCppChat does not use the Ollama client; use invoke/response instead.")

    def llama_extra_kwargs(self) -> Dict[str, Any]:
        """Keyword arguments merged into ``create_chat_completion`` (temperature, tools, etc.)."""
        extra: Dict[str, Any] = {"temperature": self.chat_temperature}
        tools = self.get_tools_for_api()
        if tools:
            for tool in tools:
                props = tool.get("function", {}).get("parameters", {}).get("properties", {})
                for _prop, obj in props.items():
                    if isinstance(obj.get("type"), list):
                        obj["type"] = obj["type"][0]
            extra["tools"] = tools
            if self.tool_choice in (None, "auto"):
                extra["tool_choice"] = "auto"
            elif isinstance(self.tool_choice, dict):
                extra["tool_choice"] = self.tool_choice
            else:
                extra["tool_choice"] = self.tool_choice
        return extra

    def _phi_messages_to_chat(self, messages: List[Message]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for m in messages:
            if m.role == "tool":
                out.append(
                    {
                        "role": "tool",
                        "content": m.get_content_string(),
                        "tool_call_id": m.tool_call_id or "",
                    }
                )
                continue
            entry: Dict[str, Any] = {"role": m.role, "content": m.get_content_string() or ""}
            if m.name:
                entry["name"] = m.name
            if m.role == "assistant" and m.tool_calls:
                entry["tool_calls"] = m.tool_calls
            out.append(entry)
        return out

    def _openai_completion_to_ollama_shape(self, completion: Mapping[str, Any]) -> Dict[str, Any]:
        choice0 = completion["choices"][0]
        msg = choice0["message"]
        usage = completion.get("usage") or {}
        tool_calls = msg.get("tool_calls")
        ollama_blocks: List[Dict[str, Any]] = []
        if tool_calls:
            for tc in tool_calls:
                fn = tc.get("function") or {}
                name = fn.get("name")
                args_raw = fn.get("arguments")
                if isinstance(args_raw, str):
                    try:
                        args_obj = json.loads(args_raw) if args_raw.strip() else {}
                    except json.JSONDecodeError:
                        args_obj = {"raw": args_raw}
                elif isinstance(args_raw, dict):
                    args_obj = args_raw
                else:
                    args_obj = {}
                ollama_blocks.append({"function": {"name": name, "arguments": args_obj}})
        inner: Dict[str, Any] = {
            "role": msg.get("role", "assistant"),
            "content": msg.get("content"),
            "tool_calls": ollama_blocks if ollama_blocks else None,
        }
        return {
            "message": inner,
            "prompt_eval_count": usage.get("prompt_tokens", 0),
            "eval_count": usage.get("completion_tokens", 0),
            "done": True,
        }

    def _openai_stream_chunk_to_ollama(self, chunk: Mapping[str, Any]) -> Dict[str, Any]:
        choice0 = chunk["choices"][0]
        delta = choice0.get("delta") or {}
        finish_reason = choice0.get("finish_reason")
        content = delta.get("content") or ""
        message: Dict[str, Any] = {"role": "assistant", "content": content}
        tool_calls_delta = delta.get("tool_calls")
        if tool_calls_delta:
            blocks: List[Dict[str, Any]] = []
            for tc in tool_calls_delta:
                fn = tc.get("function") or {}
                name = fn.get("name") or ""
                args_raw = fn.get("arguments") or ""
                if isinstance(args_raw, str) and args_raw.strip():
                    try:
                        args_obj = json.loads(args_raw) if args_raw.strip().startswith("{") else {"raw": args_raw}
                    except json.JSONDecodeError:
                        args_obj = {"raw": args_raw}
                elif isinstance(args_raw, dict):
                    args_obj = args_raw
                else:
                    args_obj = {}
                blocks.append({"function": {"name": name, "arguments": args_obj}})
            message["tool_calls"] = blocks
        done = finish_reason is not None
        out: Dict[str, Any] = {"message": message, "done": done}
        if done:
            u = chunk.get("usage") or {}
            out["prompt_eval_count"] = u.get("prompt_tokens", 0)
            out["eval_count"] = u.get("completion_tokens", 0)
        return out

    def invoke(self, messages: List[Message]) -> Mapping[str, Any]:  # type: ignore[override]
        llama = self._get_llama()
        raw = llama.create_chat_completion(
            messages=cast(Any, self._phi_messages_to_chat(messages)),
            stream=False,
            **self.llama_extra_kwargs(),
        )
        if isinstance(raw, Iterator):
            raise RuntimeError("Expected non-streaming chat completion from llama_cpp.")
        return self._openai_completion_to_ollama_shape(cast(Dict[str, Any], raw))

    def invoke_stream(self, messages: List[Message]) -> Iterator[Mapping[str, Any]]:  # type: ignore[override]
        llama = self._get_llama()
        stream = llama.create_chat_completion(
            messages=cast(Any, self._phi_messages_to_chat(messages)),
            stream=True,
            **self.llama_extra_kwargs(),
        )
        if not isinstance(stream, Iterator):
            raise RuntimeError("Expected streaming iterator from llama_cpp.")
        for chunk in stream:
            yield self._openai_stream_chunk_to_ollama(cast(Dict[str, Any], chunk))

    async def ainvoke(self, messages: List[Message]) -> Mapping[str, Any]:  # type: ignore[override]
        return self.invoke(messages)

    async def ainvoke_stream(self, messages: List[Message]) -> Any:  # type: ignore[override]
        for chunk in self.invoke_stream(messages):
            yield chunk


def build_llama_cpp_chat(
    *,
    model_path: Optional[str] = None,
    model_id: Optional[str] = None,
) -> LlamaCppChat:
    """Build a ``LlamaCppChat`` from ``model_path`` / env / or path-like ``model_id``."""
    resolved = resolve_gguf_path(model_path=model_path, model_id=model_id)
    n_threads_raw = os.environ.get("LLAMA_N_THREADS")
    n_threads = int(n_threads_raw) if n_threads_raw else None
    n_ctx = int(os.environ.get("LLAMA_N_CTX", "8192"))
    return LlamaCppChat(
        id=Path(resolved).stem,
        gguf_path=resolved,
        n_ctx=n_ctx,
        n_threads=n_threads,
    )
