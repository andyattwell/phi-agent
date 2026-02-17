from datetime import date
from pathlib import Path
from typing import Optional

from phi.agent import Agent
from phi.model.ollama import Ollama


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
            "Use the transfer_task tool to hand off work to the appropriate agent. Choose the agent whose role best matches the task.",
            "Available team members:\n" + team_descriptions,
            "IMPORTANT: Do not perform the task yourself unless it is a simple clarification or summary. Delegate everything to the corresponding agent.",
            # "IMPORTANT:Do not output tool-call JSON as text; invoke the actual transfer_task tool.",
            "After an agent completes a task, you may summarize the result for the user or delegate follow-up work if needed.",
            "Use the minimum number of delegations required. Prefer a single delegation when one agent can complete the request.",
            f"The current date is: {today}",
        ]

    def _get_guidelines(self) -> list[str]:
        return [
            "Always use the transfer_task tool to delegate; do not respond with only text when a team member should handle the request.",
            "Pick the most specific agent for the task (e.g. files for file edits, coder for code, web for search).",
            "For file operations (create, edit, delete, read files) you MUST call the transfer_task_to_files_agent tool.",
            "After delegation, briefly confirm what was done or what the user should expect.",
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

    def run(self, prompt: str, stream: bool = True) -> None:
        """Run the manager with the given prompt and print the response."""
        self._agent.print_response(prompt, stream=stream)

    @property
    def agent(self) -> Agent:
        """Access the underlying phi Agent instance."""
        return self._agent
