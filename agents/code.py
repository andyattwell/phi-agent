from datetime import date
from pathlib import Path
from typing import Optional

from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools.python import PythonTools

from agent import FileToolsWithOptionalListArg


class CodeAgent:
    """Agent that generates and runs code scripts using PythonTools."""

    DEFAULT_MODEL_ID = "qwen3:1.7b"

    def __init__(
        self,
        model_id: Optional[str] = None,
        base_dir: Optional[Path] = None,
        pip_install: bool = True,
        run_code: bool = True,
    ):
        self.model_id = model_id or self.DEFAULT_MODEL_ID
        self.base_dir = (base_dir or Path("./").resolve()).resolve()
        self.pip_install = pip_install
        self.run_code = run_code
        self._agent = self._build_agent()

    def _get_instructions(self) -> list[str]:
        today = date.today()
        return [
            "Generate code (Python or other languages as requested) to fulfill the user's request.",
            "When the user asks for a script or code: produce complete, runnable code. Use the appropriate tool to save and run it when run_code is enabled.",
            "Prefer clear, readable code. Add minimal comments only where they help understanding.",
            "If the user asks to run or execute code, use run_python_code or save_to_file_and_run as appropriate. Install required packages with pip_install_package when needed and pip_install is enabled.",
            "When returning code in your response, use markdown code blocks with the correct language (e.g. ```python). If the user asked for 'only code', omit long explanations and return the code first.",
            "Use the minimum number of tool calls required. Do not run code unnecessarily when the user only asked for the code.",
            f"The current date is: {today}",
        ]

    def _get_guidelines(self) -> list[str]:
        return [
            "Return runnable code; do not respond with pseudocode or placeholders unless the user explicitly asks for a sketch.",
            "When the user says 'only code' or 'just the code', return the code with minimal or no explanation.",
            "When running code, report any errors or output accurately. If a dependency is missing and pip_install is enabled, install it and retry when reasonable.",
            "Do not execute code that could be destructive (e.g. delete files, format disks) unless the user clearly requested it.",
            "IMPORTANT: Output only code, no other text or explanation."
        ]

    def _build_agent(self) -> Agent:
        model = Ollama(id=self.model_id)
        python_tools = PythonTools(
            base_dir=self.base_dir,
            pip_install=self.pip_install,
            run_code=self.run_code,
        )
        return Agent(
            name="Code Agent",
            role="Code Generation Agent",
            goal="Generate and run code scripts to fulfill user requests",
            description="The Code Agent generates Python and other code. It can save scripts, run them, and install dependencies when allowed.",
            model=model,
            tools=[python_tools, FileToolsWithOptionalListArg(base_dir=self.base_dir)],
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
