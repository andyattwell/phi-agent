import sys
import json
from datetime import date
from pathlib import Path
from typing import Optional
from phi.agent import Agent
from phi.tools.file import FileTools

from agents.llama_cpp_phi import build_llama_cpp_chat
from phi.utils.log import logger

class FileToolsWithOptionalListArg(FileTools):
    """FileTools with list_files accepting optional file_name and edit_file for safe in-place edits."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(self.edit_file)

    def list_files(self, file_name: Optional[str] = None) -> str:
        """Returns a list of files in the base directory. file_name is optional and ignored; use read_file to read a specific file."""
        try:
            logger.info(f"Listing files in: {self.base_dir}")
            return json.dumps([str(p) for p in self.base_dir.iterdir()], indent=4)
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return f"Error listing files: {e}"

    def edit_file(
        self,
        file_name: str,
        old_text: str,
        new_text: str,
        replace_all: bool = True,
    ) -> str:
        """Replace old_text with new_text in file_name. Preserves all other content.
        Use this for edits so the file is not overwritten with partial content.
        :param file_name: Path to the file relative to the project folder.
        :param old_text: The exact string to find (include surrounding newlines/spaces if needed).
        :param new_text: The string to replace it with.
        :param replace_all: If True, replace every occurrence; if False, replace only the first.
        :return: Success or error message.
        """
        try:
            file_path = self.base_dir / file_name
            if not file_path.exists():
                return f"Error: file not found: {file_name}"
            contents = file_path.read_text()
            if old_text not in contents:
                return (
                    f"Error: old_text not found in {file_name}. "
                    "Use read_file first to get the exact string to replace (including spaces and newlines)."
                )
            if replace_all:
                new_contents = contents.replace(old_text, new_text)
            else:
                new_contents = contents.replace(old_text, new_text, 1)
            file_path.write_text(new_contents)
            logger.info(f"Edited: {file_path}")
            return f"Successfully updated {file_name}"
        except Exception as e:
            logger.error(f"Error editing file: {e}")
            return f"Error editing file: {e}"


class FilesAgent:
    """Agent that manages files in a project folder: list, read, create, and edit files."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_id: Optional[str] = None,
        project_dir: Optional[Path] = None,
    ):
        self.model_path = model_path
        self.model_id = model_id
        self.project_dir = (project_dir or Path("./").resolve()).resolve()
        self._agent = self._build_agent()

    def _get_instructions(self) -> list[str]:
        today = date.today()
        return [
            "Use list_files() to list files in the project folder when the user asks what files exist or to discover file names.",
            "Use read_file(file_name) to read the contents of a file. Always use the file name or path relative to the project folder.",
            "To create or write a new file: call save_file(contents, file_name) with the full contents and the target file name.",
            "To edit an existing file, PREFER edit_file(file_name, old_text, new_text): (1) call read_file(file_name) to get the exact current text, (2) call edit_file with the exact old_text to find and the new_text to replace it with. This preserves all other content and avoids overwriting the file. Use replace_all=True (default) to change every occurrence, or replace_all=False to change only the first.",
            "Only use save_file for edits when you must change the entire file (e.g. large rewrites). When using save_file for edits: read_file first, then pass the complete modified content to save_file—never pass only the changed part.",
            "When the user asks to 'replace X with Y': read_file to get the exact string X, then call edit_file(file_name, X, Y).",
            "Only access files inside the project folder. Use paths relative to the base directory.",
            "When editing files, preserve existing line breaks, spaces, and indentation. Do not add extra sections, headings, or commentary unless the user asked for them.",
            "After completing a write or edit, validate the result (e.g. by reading the file back if needed) and confirm the action succeeded.",
            "Use the minimum number of tool calls required to complete the request.",
            f"The current date is: {today}",
        ]

    def _get_guidelines(self) -> list[str]:
        return [
            "Always call the appropriate tool: list_files to list, read_file to read, edit_file to edit, save_file to create or fully overwrite. Do not respond with only text or instructions—perform the tool call.",
            "When asked to create or write a new file, call save_file with the file name and full contents.",
            "When editing an existing file: prefer edit_file(file_name, old_text, new_text). Call read_file first to get the exact old_text (including spaces and newlines), then call edit_file. Do not use save_file for small edits—it can overwrite and erase content if the full file is not passed.",
            "If you must use save_file for an edit, read_file first and pass the complete file content with only the requested change; never pass only the changed part.",
            "Do not add headings like '## Updated' or duplicate content unless the user asked. Replace only what the user asked to replace.",
            "Only access files within the project folder. Do not read or write outside the base directory.",
            "After completing the request, briefly confirm what was done (e.g. file path and outcome).",
        ]

    def _build_agent(self) -> Agent:
        model = build_llama_cpp_chat(model_path=self.model_path, model_id=self.model_id)
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
