import re
import json
from datetime import date
from pathlib import Path
from typing import Optional, Any

from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools import Function


def _patch_transfer_function_additional_info() -> None:
    """Make transfer_task's additional_information accept None (phi expects str, model often sends None)."""
    from phi.agent.agent import Agent as PhiAgent

    if getattr(PhiAgent, "_transfer_patched", False):
        return
    _original_get_transfer = PhiAgent.get_transfer_function

    def _patched_get_transfer(self: Any, member_agent: Any, index: int) -> Function:
        fn = _original_get_transfer(self, member_agent, index)
        if fn.entrypoint is None:
            return fn
        original_entrypoint = fn.entrypoint

        def _entrypoint_with_default(
            task_description: str, expected_output: str, additional_information: Optional[str] = None
        ) -> Any:
            safe_info = "" if additional_information is None else additional_information
            return original_entrypoint(task_description, expected_output, safe_info)

        fn.entrypoint = _entrypoint_with_default
        # Ensure parameter schema allows optional additional_information (remove from required if present)
        if "required" in fn.parameters and "additional_information" in fn.parameters.get("required", []):
            fn.parameters["required"] = [
                r for r in fn.parameters["required"]
                if r != "additional_information"
            ]
        return fn

    PhiAgent.get_transfer_function = _patched_get_transfer
    PhiAgent._transfer_patched = True


# Apply once at import so all Agents get the patched transfer behaviour
_patch_transfer_function_additional_info()


class OrchestrationAgent:
    """Orchestration agent that routes tasks to a team of specialized agents."""

    DEFAULT_MODEL_ID = "qwen3:1.7b"

    def __init__(
        self,
        team: list[Agent],
        model_id: Optional[str] = None,
    ):
        if not team:
            raise ValueError("Orchestration requires at least one agent in the team.")
        # Accept wrapper classes (e.g. WebAgent, FilesAgent) that expose .agent
        self.team = [getattr(member, "agent", member) for member in team]
        self.model_id = model_id or self.DEFAULT_MODEL_ID
        self._agent = self._build_agent()

    def _get_instructions(self) -> list[str]:
        today = date.today()
        team_descriptions = "\n".join(
            f"- {a.name}: {getattr(a, 'role', a.name)}" for a in self.team
        )
        return [
            "You are the orchestration agent. Your job is to understand the user's request and delegate to the right team member.",
            "Do not perform the task yourself unless it is a simple clarification or summary. Delegate all operations to the corresponding team member.",
            "Use the transfer_task tool to hand off work to the appropriate agent. Choose the agent whose role best matches the task.",
            "When calling a transfer_task_to_*_agent tool you MUST provide: task_description (what to do), expected_output (what you expect), and additional_information (use the user's request or '' if none).",
            "Available team members:\n" + team_descriptions,
            "After a Files, Code, or other actionable agent completes a task (e.g. file edit, code run, file create), you MUST delegate to the Validation Agent to verify the request was fulfilled. Pass the original user request as task_description and a brief summary of what was done as additional_information. Do not skip validation for file or code tasks.",
            "For simple web search or informational answers, you do not need to call the Validation Agent.",
            "After an agent completes a task, you may summarize the result for the user or delegate follow-up work if needed.",
            "Use the minimum number of delegations required. Prefer a single delegation when one agent can complete the request, then add a validation delegation when the task involved files or code.",
            f"The current date is: {today}",
        ]

    def _get_guidelines(self) -> list[str]:
        return [
            "Always use the transfer_task tool to delegate; do not respond with only text when a team member should handle the request.",
            "When calling transfer_task_to_*_agent always pass all three arguments: task_description, expected_output, and additional_information (string; use '' if you have nothing to add).",
            "Pick the most specific agent for the task (e.g. files for file edits, coder for code, web for search).",
            "For file operations (create, edit, delete, read files) you MUST call transfer_task to the files agent.",
            "For code operations (generate, run, install dependencies) you MUST call transfer_task to the code agent.",
            "For web operations (search the web) you MUST call transfer_task to the web agent.",
            # "After the files agent or code agent completes a task, you MUST call transfer_task to the validation agent with the original user request so it can verify the work was fulfilled. For web-only answers, skip validation.",
            "IMPORTANT: Output tool-call JSON as text; dont invoke the actual transfer_task tool",
        ]

    def _build_agent(self) -> Agent:
        model = Ollama(id=self.model_id)
        return Agent(
            name="Orchestration Agent",
            role="Orchestration Agent",
            goal="Route user requests to the right team member and coordinate responses",
            description="The Manager Agent coordinates a team of agents. It delegates tasks to the appropriate specialist and returns or summarizes results.",
            model=model,
            team=self.team,
            instructions=self._get_instructions(),
            guidelines=self._get_guidelines(),
            markdown=True,
            show_tool_calls=True,
        )

    def _parse_raw_tool_call(self, response_text: str) -> Optional[tuple[str, dict[str, Any]]]:
        """If the model output raw JSON instead of invoking the tool, parse it and return (tool_name, parameters) or None."""
        if not response_text or "transfer_task" not in response_text or "parameters" not in response_text:
            return None
        # Match tool name: "name": transfer_task_to_xxx_agent or "name": "transfer_task_to_xxx_agent"
        name_match = re.search(r'"name"\s*:\s*(?:"([^"]+)"|(\w+))', response_text)
        if not name_match:
            return None
        tool_name = (name_match.group(1) or name_match.group(2) or "").strip()
        if not tool_name.startswith("transfer_task_to_") or not tool_name.endswith("_agent"):
            return None
        # Extract parameters JSON: from "parameters": { ... }
        params_match = re.search(r'"parameters"\s*:\s*(\{[^}]*(?:\{[^}]*\}[^}]*)*\})', response_text)
        if params_match:
            try:
                params = json.loads(params_match.group(1))
                return (tool_name, params)
            except json.JSONDecodeError:
                pass
        # Fallback: extract task_description only
        task_match = re.search(r'"task_description"\s*:\s*"((?:[^"\\]|\\.)*)"', response_text)
        if task_match:
            return (tool_name, {"task_description": task_match.group(1).encode().decode("unicode_escape")})
        return None

    def _tool_name_to_agent(self, tool_name: str) -> Optional[Agent]:
        """Map transfer_task_to_<slug>_agent to the corresponding team agent by name."""
        # transfer_task_to_files_agent -> "files" -> match agent with "Files" in name
        prefix = "transfer_task_to_"
        suffix = "_agent"
        if not tool_name.startswith(prefix) or not tool_name.endswith(suffix):
            return None
        slug = tool_name[len(prefix) : -len(suffix)]
        slug_lower = slug.lower()
        for a in self.team:
            name = getattr(a, "name", "") or ""
            # "Files Agent" -> "files", "Coder Agent" -> "coder", "Web Agent" -> "web"
            first_word = name.split()[0].lower() if name else ""
            if first_word == slug_lower or slug_lower in name.lower():
                return a
        return None

    def run(self, prompt: str, stream: bool = True) -> None:
        """Run the manager with the given prompt and print the response.
        When the model outputs raw JSON instead of invoking the transfer_task tool,
        this method detects it and delegates to the correct team agent anyway."""
        
        # self._agent.print_response(prompt, stream=stream)

        print(f"Running manager with prompt: {prompt}")
        response = self._agent.run(prompt, stream=False)
        response_text = getattr(response, "content", None) or getattr(response, "content_str", None)
        if response_text is None and hasattr(response, "messages") and response.messages:
            last = response.messages[-1]
            response_text = getattr(last, "content", None) or str(last)
        if response_text is None:
            response_text = str(response)
        parsed = self._parse_raw_tool_call(response_text)
        if parsed:
            tool_name, params = parsed
            agent = self._tool_name_to_agent(tool_name)
            if agent:
                task_description = params.get("task_description") or params.get("task") or prompt
                print(f"[Orchestrator delegated to {getattr(agent, 'name', tool_name)}]\n")
                agent.print_response(task_description, stream=stream)
                return
        print(response_text)

    @property
    def agent(self) -> Agent:
        """Access the underlying phi Agent instance."""
        return self._agent
