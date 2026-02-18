
from typing import Optional
from pathlib import Path
from files import FileToolsWithOptionalListArg
from base_agent import BaseAgent


class DocumentAgent(BaseAgent):
    """Agent that creates and updates documentation after an implementation."""

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
            name="Document Agent",
            role="Documentation Agent",
            goal="Create and update documentation after an implementation",
            description="You are an expert software documentation writer. You are given an implementation report and you need to create and update documentation to reflect the implementation.",
            tools=[FileToolsWithOptionalListArg(base_dir=self.base_dir)],
            workspace_id=self.workspace_id,
            base_dir=self.base_dir,
            command="document",
        )

    def _get_prompt(self, implementation_report: str) -> str:
        cmds_path = self.base_dir / "agents" / "commands"
        with open(cmds_path / "document.md", "r") as file:
            doc_prompt = file.read()
        doc_prompt = doc_prompt.replace("{{implementation_report}}", implementation_report)
        doc_prompt = doc_prompt.replace("{{base_dir}}", str(self.base_dir))
        return doc_prompt

    def run(self, implementation_report: str, stream: bool = False) -> str:
        """Run the agent to create or update documentation from the implementation report."""
        print("Running documentation agent...")
        print(f"Implementation report: \n\n{implementation_report}\n\n")

        prompt = self._get_prompt(implementation_report)
        self._agent.print_response(prompt, stream=stream)
