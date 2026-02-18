
from typing import Optional
from pathlib import Path
from phi.tools.python import PythonTools
from phi.tools.shell import ShellTools
from files import FileToolsWithOptionalListArg
from base_agent import BaseAgent


class TestAgent(BaseAgent):
    """Agent that tests the implementation plan."""

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
            name="Test Agent",
            role="Test Agent",
            goal="Test the implementation plan",
            description="You are an expert QA Engineer. You are given an implementation plan and you need to test the implementation to ensure it fulfills the user request and is working as expected.",
            tools=[
                PythonTools(base_dir=self.base_dir, pip_install=True, run_code=True),
                FileToolsWithOptionalListArg(base_dir=self.base_dir),
                ShellTools(),
            ],
            workspace_id=self.workspace_id,
            base_dir=self.base_dir,
            command="test",
        )

    def _get_prompt(self, plan: str, implementation: str) -> str:
        cmds_path = f"{self.base_dir}/agents/commands"
        with open(f"{cmds_path}/test.md", "r") as file:
            test_prompt = file.read()
        test_prompt = test_prompt.replace("{{implementation_plan}}", plan)
        test_prompt = test_prompt.replace("{{implementation}}", implementation)
        return test_prompt

    def run(self, plan: str, implementation: str, stream: bool = True) -> str:
        """Run the agent with the given prompt and print the response."""
        print("Running test for plan...")
        print(f"Plan: \n\n{plan}\n\n")
        print(f"Implementation: \n\n{implementation}\n\n")

        test_prompt = self._get_prompt(plan, implementation)
        self._agent.print_response(test_prompt, stream=stream)
