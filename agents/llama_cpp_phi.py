"""Phi ``Model`` backed by a running **llama.cpp server** (HTTP OpenAI-compatible API).

Subclasses ``phi.model.ollama.chat.Ollama`` so ``response`` / ``response_stream`` and tool
execution match the Ollama integration, while ``invoke`` / ``invoke_stream`` POST to
``{LLAMA_SERVER_URL}/v1/chat/completions`` (same shape as ``adw/providers/llama-cpp-provider.ts``).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple, cast

from pydantic import Field

from phi.model.message import Message
from phi.model.ollama.chat import Ollama


def resolve_gguf_path(
    *,
    model_path: Optional[str] = None,
    model_id: Optional[str] = None,
    env_var: str = "LLAMA_MODEL_PATH",
) -> str:
    """Resolve a local GGUF path (optional; used only to derive a default ``model`` id for the server)."""
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
        f"No local GGUF path for {env_var}: pass model_path=... or set the env var "
        "(only needed if LLAMA_SERVER_MODEL is unset)."
    )


def _default_server_model_id(*, model_path: Optional[str], model_id: Optional[str]) -> str:
    env = os.environ.get("LLAMA_SERVER_MODEL", "").strip()
    if env:
        return env
    try:
        return Path(resolve_gguf_path(model_path=model_path, model_id=model_id)).stem
    except (ValueError, FileNotFoundError):
        return os.environ.get("LLAMA_SERVER_MODEL_FALLBACK", "gpt-3.5-turbo")


class _AccTool:
    __slots__ = ("id", "name", "args")

    def __init__(self) -> None:
        self.id: Optional[str] = None
        self.name: str = ""
        self.args: str = ""


def _apply_tool_deltas(acc: Dict[int, _AccTool], deltas: List[Mapping[str, Any]]) -> None:
    for d in deltas:
        idx = int(d.get("index", 0))
        cur = acc.get(idx) or _AccTool()
        if d.get("id"):
            cur.id = str(d["id"])
        fn = d.get("function") or {}
        if isinstance(fn, dict):
            if fn.get("name"):
                cur.name += str(fn["name"])
            if fn.get("arguments") is not None:
                cur.args += str(fn["arguments"])
        acc[idx] = cur


def _finalize_acc_tools(acc: Dict[int, _AccTool]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for k in sorted(acc.keys()):
        t = acc[k]
        args_obj: Dict[str, Any] = {}
        if t.args.strip():
            try:
                args_obj = json.loads(t.args)
            except json.JSONDecodeError:
                args_obj = {}
        fn: Dict[str, Any] = {"name": t.name, "arguments": json.dumps(args_obj)}
        tc: Dict[str, Any] = {"type": "function", "function": fn}
        if t.id:
            tc["id"] = t.id
        out.append(tc)
    return out


def _parse_chat_template_kwargs() -> Optional[Dict[str, Any]]:
    raw = os.environ.get("LLAMA_CHAT_TEMPLATE_KWARGS", "").strip()
    if not raw:
        return None
    try:
        return cast(Dict[str, Any], json.loads(raw))
    except json.JSONDecodeError:
        return None


class LlamaServerChat(Ollama):
    """OpenAI-compatible chat against ``llama-server`` (or any compatible host)."""

    name: str = "LlamaServer"
    provider: str = "LlamaServer"

    base_url: str = Field(
        default="http://127.0.0.1:8088",
        description="Base URL of llama.cpp server (no trailing slash).",
    )
    timeout_seconds: float = Field(
        default=600.0,
        description="HTTP timeout in seconds for chat completion requests.",
    )
    chat_temperature: float = Field(default=0.2, description="Sampling temperature for chat completion.")

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        object.__setattr__(self, "base_url", str(self.base_url).rstrip("/"))

    def get_client(self) -> Any:  # type: ignore[override]
        raise RuntimeError("LlamaServerChat uses HTTP only; use invoke/response instead.")

    def _request_url(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    def _base_request_body(self, messages: List[Dict[str, Any]], *, stream: bool) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "model": self.id,
            "messages": messages,
            "stream": stream,
            "temperature": self.chat_temperature,
            "parse_tool_calls": True,
        }
        kwargs = _parse_chat_template_kwargs()
        if kwargs is not None:
            body["chat_template_kwargs"] = kwargs
        if stream:
            body["stream_options"] = {"include_usage": True}
        tools = self.get_tools_for_api()
        if tools:
            for tool in tools:
                props = tool.get("function", {}).get("parameters", {}).get("properties", {})
                for _prop, obj in props.items():
                    if isinstance(obj.get("type"), list):
                        obj["type"] = obj["type"][0]
            body["tools"] = tools
            if self.tool_choice in (None, "auto"):
                body["tool_choice"] = "auto"
            elif isinstance(self.tool_choice, dict):
                body["tool_choice"] = self.tool_choice
            else:
                body["tool_choice"] = self.tool_choice
        return body

    def _phi_messages_to_openai(self, messages: List[Message]) -> List[Dict[str, Any]]:
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
            content = m.get_content_string() or ""
            entry: Dict[str, Any] = {"role": m.role, "content": content}
            if m.name:
                entry["name"] = m.name
            if m.role == "assistant" and m.tool_calls:
                openai_tcs: List[Dict[str, Any]] = []
                for j, tc in enumerate(m.tool_calls):
                    if not isinstance(tc, dict):
                        continue
                    fn = tc.get("function") or {}
                    name = fn.get("name", "") or ""
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        args_str = args
                    else:
                        args_str = json.dumps(args if args is not None else {})
                    tid = (tc.get("id") or f"call_{j}").strip() if isinstance(tc.get("id"), str) else f"call_{j}"
                    openai_tcs.append(
                        {
                            "id": tid,
                            "type": "function",
                            "function": {"name": name, "arguments": args_str},
                        }
                    )
                entry["tool_calls"] = openai_tcs
                if not content.strip():
                    entry["content"] = None
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

    def _http_post(self, body: Dict[str, Any], *, stream: bool) -> Tuple[int, Any]:
        import urllib.error
        import urllib.request

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self._request_url(),
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream" if stream else "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                status = resp.getcode()
                raw = resp.read()
                return status, raw
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"llama-server HTTP {e.code}: {err_body or e.reason}") from e

    def _consume_sse_stream(self, raw_bytes: bytes) -> Dict[str, Any]:
        """Parse full SSE body into a single OpenAI-style chat completion object."""
        text = raw_bytes.decode("utf-8", errors="replace")
        content_parts: List[str] = []
        reasoning_parts: List[str] = []
        tool_acc: Dict[int, _AccTool] = {}
        last_usage: Dict[str, Any] = {}

        for line in text.splitlines():
            trimmed = line.strip()
            if not trimmed.startswith("data:"):
                continue
            data_line = trimmed[5:].strip()
            if not data_line or data_line == "[DONE]":
                continue
            try:
                payload = json.loads(data_line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload.get("usage"), dict):
                last_usage = payload["usage"]
            choices = payload.get("choices") or []
            if not choices:
                continue
            ch0 = choices[0]
            delta = ch0.get("delta") or {}
            msg = ch0.get("message") or {}
            if delta.get("reasoning_content"):
                reasoning_parts.append(str(delta["reasoning_content"]))
            if delta.get("content"):
                content_parts.append(str(delta["content"]))
            if delta.get("tool_calls"):
                _apply_tool_deltas(tool_acc, cast(List[Mapping[str, Any]], delta["tool_calls"]))
            if msg.get("reasoning_content"):
                reasoning_parts.append(str(msg["reasoning_content"]))
            if msg.get("content"):
                content_parts.append(str(msg["content"]))

        # Reasoning is not in standard OpenAI message; prefix for any downstream use
        main_content = "".join(content_parts)
        if reasoning_parts:
            think = "".join(reasoning_parts)
            if main_content:
                main_content = f"{think}\n\n{main_content}"
            else:
                main_content = think

        tool_calls = _finalize_acc_tools(tool_acc)
        message: Dict[str, Any] = {
            "role": "assistant",
            "content": main_content or None,
        }
        if tool_calls:
            message["tool_calls"] = tool_calls
        return {
            "choices": [{"message": message, "finish_reason": "stop"}],
            "usage": last_usage,
        }

    def invoke(self, messages: List[Message]) -> Mapping[str, Any]:  # type: ignore[override]
        openai_messages = self._phi_messages_to_openai(messages)
        body = self._base_request_body(openai_messages, stream=False)
        status, raw = self._http_post(body, stream=False)
        if status != 200:
            raise RuntimeError(f"llama-server unexpected status {status}")
        completion = json.loads(raw.decode("utf-8"))
        if not completion.get("choices"):
            raise RuntimeError(f"llama-server invalid JSON response: {completion!r}")
        return self._openai_completion_to_ollama_shape(completion)

    def invoke_stream(self, messages: List[Message]) -> Iterator[Mapping[str, Any]]:  # type: ignore[override]
        openai_messages = self._phi_messages_to_openai(messages)
        body = self._base_request_body(openai_messages, stream=True)
        status, raw = self._http_post(body, stream=True)
        if status != 200:
            raise RuntimeError(f"llama-server unexpected status {status}")
        completion = self._consume_sse_stream(raw)
        ollama_msg = self._openai_completion_to_ollama_shape(completion)
        inner = ollama_msg["message"]
        usage = completion.get("usage") or {}
        yield {
            "message": {
                "role": "assistant",
                "content": inner.get("content"),
                "tool_calls": inner.get("tool_calls"),
            },
            "done": True,
            "prompt_eval_count": usage.get("prompt_tokens", 0),
            "eval_count": usage.get("completion_tokens", 0),
        }

    async def ainvoke(self, messages: List[Message]) -> Mapping[str, Any]:  # type: ignore[override]
        return self.invoke(messages)

    async def ainvoke_stream(self, messages: List[Message]) -> Any:  # type: ignore[override]
        for chunk in self.invoke_stream(messages):
            yield chunk


# Backwards compatibility for imports
LlamaCppChat = LlamaServerChat


def build_llama_cpp_chat(
    *,
    model_path: Optional[str] = None,
    model_id: Optional[str] = None,
) -> LlamaServerChat:
    """Build a ``LlamaServerChat`` client (HTTP to llama.cpp server).

    Environment:
    - ``LLAMA_SERVER_URL`` — base URL (default ``http://127.0.0.1:8088``).
    - ``LLAMA_SERVER_MODEL`` — JSON ``model`` field (default: stem of ``LLAMA_MODEL_PATH`` if set).
    - ``LLAMA_SERVER_TIMEOUT`` — seconds (default ``600``).
    - ``LLAMA_CHAT_TEMPLATE_KWARGS`` — optional JSON object for ``chat_template_kwargs``.
    """
    base = os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8080").rstrip("/")
    mid = _default_server_model_id(model_path=model_path, model_id=model_id)
    timeout = float(os.environ.get("LLAMA_SERVER_TIMEOUT", "600"))
    temp_raw = os.environ.get("LLAMA_SERVER_TEMPERATURE", "").strip()
    temperature = float(temp_raw) if temp_raw else 0.2
    return LlamaServerChat(
        id=mid,
        base_url=base,
        timeout_seconds=timeout,
        chat_temperature=temperature,
    )
