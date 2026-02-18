
from typing import Optional
from pathlib import Path
from phi.tools.python import PythonTools
from phi.tools.shell import ShellTools
from files import FileToolsWithOptionalListArg
from base_agent import BaseAgent


class ImplementationAgent(BaseAgent):
    """Agent that generates and runs code scripts using PythonTools."""

    def __init__(
        self,
        model_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        base_dir: Optional[Path] = None,
    ):
        self.model_id = model_id
        self.workspace_id = workspace_id or "default"
        self.base_dir = (base_dir or Path("./").resolve()).resolve()
        super().__init__(
            name="Implementation Agent", 
            role="Implementation Agent", 
            goal=f"Generate and run code scripts to fulfill the user request", 
            description="You are an expert software developer. You are given an implementation plan and you need to generate and run code scripts to fulfill the user request.", 
            tools=[PythonTools(base_dir=self.base_dir, pip_install=True, run_code=True), FileToolsWithOptionalListArg(base_dir=self.base_dir), ShellTools()], 
            workspace_id=self.workspace_id, 
            base_dir=self.base_dir,
        )

    def _get_prompt(self, prompt: str) -> str:
        cmds_path = f"{self.base_dir}/agents/commands"
        with open(f"{cmds_path}/implementatoion.md", "r") as file:
            implement_prompt = file.read()
        implement_prompt = implement_prompt.replace("{{implementation_plan}}", prompt)
        return implement_prompt

    def run(self, prompt: str, stream: bool = True) -> None:
        """Run the agent with the given prompt and print the response."""
        # self._agent.print_response(prompt, stream=stream)

        print(f"Running implementation plan")
        print(f"Prompt: \n\n{prompt}\n\n")

        implement_prompt = self._get_prompt(prompt)
        self.agent.print_response(implement_prompt, stream=stream)
  

