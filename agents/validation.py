import json
from datetime import date
from pathlib import Path
from typing import Optional

from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools.file import FileTools
from phi.utils.log import logger


class ReadOnlyFileTools(FileTools):
    """FileTools restricted to listing and reading only (no write/edit)."""

    def list_files(self, file_name: Optional[str] = None) -> str:
        """Returns a list of files in the base directory. file_name is optional and ignored; use read_file to read a specific file."""
        try:
            logger.info(f"Listing files in: {self.base_dir}")
            return json.dumps([str(p) for p in self.base_dir.iterdir()], indent=4)
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return f"Error listing files: {e}"


class ValidationAgent:
    """Agent that validates work done by other agents by checking if the original request was fulfilled."""

    DEFAULT_MODEL_ID = "qwen3:1.7b"

    def __init__(
        self,
        model_id: Optional[str] = None,
        project_dir: Optional[Path] = None,
    ):
        self.model_id = model_id or self.DEFAULT_MODEL_ID
        self.project_dir = (project_dir or Path("./").resolve()).resolve()
        self._agent = self._build_agent()

    def _get_instructions(self) -> list[str]:
        today = date.today()
        return [
            "You are the Validation Agent. Your job is to verify that a previous user request was fulfilled by inspecting the current state of the project.",
            "You will receive: (1) the original user request (task_description), and (2) optional context about what was done (expected_output or additional_information).",
            "Use list_files() to see what files exist in the project. Use read_file(file_name) to read the contents of files that are relevant to the request.",
            "Check that the expected outcome is present: e.g. a new file was created with the right content, an existing file was edited as requested, or code was added/run as described.",
            "Do not modify any files. You only inspect and report.",
            "At the end of your response, state clearly one of: FULFILLED, NOT FULFILLED, or PARTIAL, followed by a short explanation of what you found.",
            "Use the minimum number of tool calls needed to verify the request. Focus on the files or artifacts that the request referred to.",
            f"The current date is: {today}",
        ]

    def _get_guidelines(self) -> list[str]:
        return [
            "Always use list_files and/or read_file to inspect the project before concluding. Do not assume the request was fulfilled without checking.",
            "When the request referred to a specific file or path, read that file and verify the expected content or changes are present.",
            "Report FULFILLED only when the evidence (file contents, file existence) matches the original request. Report NOT FULFILLED when key expectations are missing. Report PARTIAL when some but not all aspects were done.",
            "Keep your verification report concise. Quote or reference specific file content only when it helps justify your conclusion.",
            "Only read files within the project folder. Do not attempt to edit or create files.",
        ]

    def _build_agent(self) -> Agent:
        model = Ollama(id=self.model_id)
        return Agent(
            name="Validation Agent",
            role="Validation Agent",
            goal="Verify that user requests were fulfilled by inspecting project state",
            description="The Validation Agent checks whether work done by other agents fulfilled the user's request. It uses read-only file access to list and read files and reports FULFILLED, NOT FULFILLED, or PARTIAL with a short explanation.",
            model=model,
            tools=[ReadOnlyFileTools(base_dir=self.project_dir)],
            instructions=self._get_instructions(),
            guidelines=self._get_guidelines(),
            markdown=True,
            show_tool_calls=True,
        )

    def run(self, prompt: str, stream: bool = True) -> None:
        """Run the agent with the given prompt and print the response."""
        self._agent.print_response(prompt, stream=stream)

    @property
    def agent(self) -> Agent:
        """Access the underlying phi Agent instance."""
        return self._agent
