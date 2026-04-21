from datetime import date
import os
from pathlib import Path
from typing import Any, Optional

from phi.agent import Agent

from agents.llama_cpp_phi import build_llama_cpp_chat


class BaseAgent:
    """Base class for all agents."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        base_dir: Optional[Path] = None,
        name: Optional[str] = None,
        role: Optional[str] = None,
        goal: Optional[str] = None,
        description: Optional[str] = None,
        tools: Optional[list[Any]] = None,
        command: Optional[str] = None,
        team: Optional[list[Agent]] = None,
    ):
        self.model_path = model_path
        self.model_id = model_id
        self.workspace_id = workspace_id
        self.base_dir = (base_dir or Path("./").resolve()).resolve()
        self.name = name or self.name
        self.role = role
        self.goal = goal
        self.description = description
        self.tools = tools
        self.command = command
        self.cmds_path = f"{self.base_dir}/agents/commands"
        self.team = team
        self._agent = self._build_agent()

    def _get_instructions(self) -> list[str]:
        today = date.today()
        instructions = []
        with open(f"{self.cmds_path}/agent.md", "r") as file:
            agent_prompt = file.read()
        instructions.extend(agent_prompt.split("\n"))
        # If instructions file exists, add it to the instructions
        if os.path.exists(f"{self.cmds_path}/instructions/{self.command}.md"):
            with open(f"{self.cmds_path}/instructions/{self.command}.md", "r") as file:
                instructions_prompt = file.read()
            instructions.extend(instructions_prompt.split("\n"))

        # Add the current date to the instructions
        instructions.append(f"The current date is: {today}")
        return instructions

    def _get_guidelines(self) -> list[str]:
        guidelines = []
        # If guidelines file exists, add it to the guidelines
        if os.path.exists(f"{self.cmds_path}/guidelines/{self.command}.md"):
            with open(f"{self.cmds_path}/guidelines/{self.command}.md", "r") as file:
                guidelines_prompt = file.read()
            guidelines.extend(guidelines_prompt.split("\n"))
        return guidelines

    def _get_prompt(self, prompt: str) -> str:

        # If prompt file exists, add it to the prompt
        if os.path.exists(f"{self.cmds_path}/{self.command}.md"):
            with open(f"{self.cmds_path}/{self.command}.md", "r") as file:
                prompt_template = file.read()
            prompt_template = prompt_template.replace("{{prompt}}", prompt)
            prompt_template = prompt_template.replace("{{base_dir}}", str(self.base_dir))
            prompt_template = prompt_template.replace("{{workspace_id}}", self.workspace_id)
            return prompt_template
        return prompt

    def _build_agent(self) -> Agent:
        
        return Agent(
            name=self.name,
            role=self.role,
            goal=self.goal,
            team=self.team,
            description=self.description,
            model=build_llama_cpp_chat(model_path=self.model_path, model_id=self.model_id),
            tools=self.tools,
            instructions=self._get_instructions(),
            guidelines=self._get_guidelines(),
            markdown=True,
            show_tool_calls=True,
        )

    def run(self, prompt: str, stream: bool = True) -> None:
        """Run the agent with the given prompt and print the response."""
        prompt = self._get_prompt(prompt)
        self._agent.print_response(prompt, stream=stream)

    @property
    def agent(self) -> Agent:
        """Access the underlying phi Agent instance."""
        return self._agent