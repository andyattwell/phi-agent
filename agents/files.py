import sys
import json
from datetime import date
from pathlib import Path
from typing import Optional
from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools.file import FileTools
from phi.utils.log import logger

class FileToolsWithOptionalListArg(FileTools):
    """FileTools with list_files accepting optional file_name so the model can call list_files(file_name='x') without validation error."""

    def list_files(self, file_name: Optional[str] = None) -> str:
        """Returns a list of files in the base directory. file_name is optional and ignored; use read_file to read a specific file."""
        try:
            logger.info(f"Listing files in: {self.base_dir}")
            return json.dumps([str(p) for p in self.base_dir.iterdir()], indent=4)
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return f"Error listing files: {e}"


class FilesAgent:
    """Agent that manages files in a project folder: list, read, create, and edit files."""

    # Model notes: qwen3 (slow), qwen3:1.7b (inaccurate, extra tool calls), llama3.2 (works, less accurate)
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
            "Use list_files() to list files in the project folder when the user asks what files exist or to discover file names.",
            "Use read_file(file_name) to read the contents of a file. Always use the file name or path relative to the project folder.",
            "To create or write a new file: call save_file(contents, file_name) with the full contents and the target file name.",
            "To edit an existing file you MUST: (1) call read_file(file_name) first to get the entire current content, (2) make only the requested change in that content (e.g. replace the exact phrase the user asked to replace with the new text), (3) call save_file with the complete modified content—every line and character that was not changed must remain unchanged. The first argument to save_file must be the full file content, not a summary or only the changed part.",
            "When the user asks to 'replace X with Y' in a file: read the file, then pass to save_file a string that is the original content with every occurrence of X changed to Y. All other lines and text must be preserved exactly.",
            "Only access files inside the project folder. Use paths relative to the base directory.",
            "When editing files, preserve existing line breaks, spaces, and indentation. Do not add extra sections, headings, or commentary to the file unless the user asked for them.",
            "After completing a write or edit, validate the result (e.g. by reading the file back if needed) and confirm the action succeeded.",
            "Use the minimum number of tool calls required to complete the request.",
            f"The current date is: {today}",
        ]

    def _get_guidelines(self) -> list[str]:
        return [
            "Always call the appropriate tool for the task: list_files to list, read_file to read, save_file to write or overwrite. Do not respond with only text or instructions—perform the tool call.",
            "When asked to create or write a file, you must call save_file with the given file name and contents; do not respond with only the file content as text.",
            "When editing a file: you must read_file first. The value you pass to save_file must be the complete file content with only the requested edit applied. Never pass only the changed line or a summary—pass the full file text so that unchanged lines are preserved.",
            "Do not add headings like '## Updated' or duplicate content into the file unless the user explicitly asked for them. Edit in place: replace only what the user asked to replace.",
            "Only access files within the project folder. Do not attempt to read or write outside the base directory.",
            "After completing the request, briefly confirm what was done (e.g. file path and outcome).",
        ]

    def _build_agent(self) -> Agent:
        model = Ollama(id=self.model_id)
        return Agent(
            name="Files Agent",
            role="Files Manager Agent",
            goal="Manage files in the project folder",
            description="The Files Manager Agent is responsible for managing files in the project folder. It can create, update, delete, and find files in the project folder.",
            model=model,
            tools=[FileToolsWithOptionalListArg(base_dir=self.project_dir)],
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


# def main():
#     project_dir = Path("./").resolve()
#     files_agent = FilesAgent(model_id="qwen3:1.7b", project_dir=project_dir)
#     prompt = "edit the file test.txt. Replace the text 'This is a test' for a random title"
#     files_agent.run(prompt, stream=True)
#     sys.exit(0)


# if __name__ == "__main__":
#     main()
