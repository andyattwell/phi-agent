from datetime import date
import os
from pathlib import Path
from typing import Optional
import uuid

from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools.python import PythonTools
from phi.tools.shell import ShellTools

from files import FileToolsWithOptionalListArg


class CodeAgent:
    """Agent that generates and runs code scripts using PythonTools."""

    DEFAULT_MODEL_ID = "qwen3:1.7b"

    def __init__(
        self,
        model_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        base_dir: Optional[Path] = None,
        pip_install: bool = True,
        run_code: bool = True,
    ):
        self.model_id = model_id or self.DEFAULT_MODEL_ID
        self.workspace_id = workspace_id
        self.base_dir = (base_dir or Path("./").resolve()).resolve()
        self.pip_install = pip_install
        self.run_code = run_code
        self._agent = self._build_agent()

    def _get_instructions(self) -> list[str]:
        today = date.today()
        return [
            "Generate code in the requested language to fulfill the user's request.",
            "When the user asks for a script or code: produce complete, runnable code. Use the appropriate tool to save and run it when run_code is enabled.",
            "Prefer clear, readable code. Add minimal comments only where they help understanding.",
            "If the user asks to run or execute code, use run_python_code or save_to_file_and_run as appropriate. Install required packages with pip_install_package when needed and pip_install is enabled.",
            "When returning code in your response, use markdown code blocks with the correct language (e.g. ```python). If the user asked for 'only code', omit long explanations and return the code first.",
            "Use the minimum number of tool calls required. Do not run code unnecessarily when the user only asked for the code.",
            "Use the shell tool to run code in the requested language.",
            "Only touch files inside the project's root folder.",
            "If the work does not include modifications to the agents scripts, workflows, etc, all the files should be created in the `app/` directory.",
            f"The current date is: {today}",
        ]

    def _get_guidelines(self) -> list[str]:
        return [
            "Return runnable code; do not respond with pseudocode or placeholders unless the user explicitly asks for a sketch.",
            "When the user says 'only code' or 'just the code', return the code with minimal or no explanation.",
            "When running code, report any errors or output accurately. If a dependency is missing and pip_install is enabled, install it and retry when reasonable.",
            "Do not execute code that could be destructive (e.g. delete files, format disks) unless the user clearly requested it.",
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
            description="The Code Agent generates code in the requested language. It can save scripts, run them, and install dependencies when allowed.",
            model=model,
            tools=[
                python_tools, 
                FileToolsWithOptionalListArg(base_dir=self.base_dir),
                ShellTools(),
            ],
            instructions=self._get_instructions(),
            guidelines=self._get_guidelines(),
            markdown=True,
            show_tool_calls=True,
        )
    def _get_prompt(self, prompt: str) -> str:
        cmds_path = f"{self.base_dir}/agents/commands"
        with open(f"{cmds_path}/implement.md", "r") as file:
            implement_prompt = file.read()
        implement_prompt = implement_prompt.replace("{{implementation_plan}}", prompt)
        return implement_prompt

    def run(self, prompt: str, stream: bool = True) -> None:
        """Run the agent with the given prompt and print the response."""
        # self._agent.print_response(prompt, stream=stream)

        print(f"Running implementation plan")

        implement_prompt = self._get_prompt(prompt)

        implement_response = self._agent.run(implement_prompt, stream=False)
        implement_response_text = getattr(implement_response, "content", None) or getattr(implement_response, "content_str", None)
        
        if implement_response_text is None and hasattr(implement_response, "messages") and implement_response.messages:
            last = implement_response.messages[-1]
            implement_response_text = getattr(last, "content", None) or str(last)
        if implement_response_text is None:
            implement_response_text = str(implement_response)
        
        # save the implementation to a file
        implement_dir = f"{self.base_dir}/specs/{self.workspace_id}"
        os.makedirs(implement_dir, exist_ok=True)
        implement_file_path = f"{implement_dir}/IMPLEMENTATION.md"
        with open(f"{implement_file_path}", "w") as file:
            file.write(implement_response_text)
        
        print(f"Implementation saved to: \n{implement_file_path}\n\n")

        return implement_response_text


    @property
    def agent(self) -> Agent:
        """Access the underlying phi Agent instance."""
        return self._agent

class PlanAgent:
    """Agent that generates implementation plans."""

    DEFAULT_MODEL_ID = "qwen3:1.7b"

    def __init__(
        self,
        model_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        base_dir: Optional[Path] = None,
        pip_install: bool = True,
        run_code: bool = True,
    ):
        self.model_id = model_id or self.DEFAULT_MODEL_ID
        self.workspace_id = workspace_id
        self.base_dir = (base_dir or Path("./").resolve()).resolve()
        self.pip_install = pip_install
        self.run_code = run_code
        self._agent = self._build_agent()

    def _get_instructions(self) -> list[str]:
        today = date.today()
        cmds_path = f"{self.base_dir}/agents/commands"
        instructions = []
        with open(f"{cmds_path}/agent.md", "r") as file:
            agent_prompt = file.read()
        instructions.extend(agent_prompt.split("\n"))

        with open(f"{cmds_path}/plan-instructions.md", "r") as file:
            plan_prompt = file.read()
        instructions.extend(plan_prompt.split("\n"))
        instructions.append(f"The current date is: {today}")
        return instructions

    def _get_guidelines(self) -> list[str]:
        cmds_path = f"{self.base_dir}/agents/commands"

        with open(f"{cmds_path}/plan-guidelines.md", "r") as file:
            plan_guidelines = file.read()
        
        return plan_guidelines.split("\n")

    def _build_agent(self) -> Agent:
        model = Ollama(id=self.model_id)
        return Agent(
            name="Plan Agent",
            role="Plan Agent",
            goal="Generate a software implementation plan",
            description="Generate a step by step implementation plan for a given user prompt.",
            model=model,
            tools=[],
            instructions=self._get_instructions(),
            guidelines=self._get_guidelines(),
            markdown=True,
            show_tool_calls=True,
        )

    def _get_prompt(self, prompt: str) -> str:
        cmds_path = f"{self.base_dir}/agents/commands"
        with open(f"{cmds_path}/plan.md", "r") as file:
            plan_prompt = file.read()
        plan_prompt = plan_prompt.replace("{{prompt}}", prompt)
        plan_prompt = plan_prompt.replace("{{base_dir}}", str(self.base_dir))
        return plan_prompt

    def run(self, prompt: str, stream: bool = True) -> str:
        """Run the agent with the given prompt and print the response."""
        # self._agent.print_response(prompt, stream=stream)

        print(f"Running plan for prompt: \n\n{prompt}\n\n")

        plan_prompt = self._get_prompt(prompt)
        plan_response = self._agent.run(plan_prompt, stream=False)
        plan_response_text = getattr(plan_response, "content", None) or getattr(plan_response, "content_str", None)
        if plan_response_text is None and hasattr(plan_response, "messages") and plan_response.messages:
            last = plan_response.messages[-1]
            plan_response_text = getattr(last, "content", None) or str(last)
        if plan_response_text is None:
            plan_response_text = str(plan_response)
        

        # save the plan to a file
        plan_dir = f"{self.base_dir}/specs/{self.workspace_id}"
        os.makedirs(plan_dir, exist_ok=True)
        plan_file_path = f"{plan_dir}/IMPLEMENTATION_PLAN.md"
        with open(f"{plan_file_path}", "w") as file:
            file.write(plan_response_text)
        
        print(f"Implementation Plan saved to: \n{plan_file_path}\n\n")

        return plan_response_text


    @property
    def agent(self) -> Agent:
        """Access the underlying phi Agent instance."""
        return self._agent

class TestAgent:
    """Agent that tests the implementation plan."""

    DEFAULT_MODEL_ID = "qwen3:1.7b"

    def __init__(self, model_id: Optional[str] = None, workspace_id: Optional[str] = None, base_dir: Optional[Path] = None):
        self.model_id = model_id or self.DEFAULT_MODEL_ID
        self.base_dir = (base_dir or Path("./").resolve()).resolve()
        self.workspace_id = workspace_id
        self._agent = self._build_agent()

    def _build_agent(self) -> Agent:
        model = Ollama(id=self.model_id)
        python_tools = PythonTools(
            base_dir=self.base_dir,
            pip_install=True,
            run_code=True,
        )
        return Agent(
            name="Test Agent",
            role="Test Agent",
            goal="Test the implementation plan",
            description="Test the implementation plan for a given user prompt.",
            model=model,
            tools=[
                python_tools, 
                FileToolsWithOptionalListArg(base_dir=self.base_dir), 
                ShellTools()
            ],
            instructions=[],
            guidelines=[],
            markdown=True,
            show_tool_calls=True,
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
        # self._agent.print_response(prompt, stream=stream)

        print(f"Running test for plan...")

        test_prompt = self._get_prompt(plan, implementation)

        test_response = self._agent.run(test_prompt, stream=False)
        test_response_text = getattr(test_response, "content", None) or getattr(test_response, "content_str", None)
        
        if test_response_text is None and hasattr(test_response, "messages") and test_response.messages:
            last = test_response.messages[-1]
            test_response_text = getattr(last, "content", None) or str(last)
        if test_response_text is None:
            test_response_text = str(test_response)

        # save the test results to a file
        test_dir = f"{self.base_dir}/specs/{self.workspace_id}"
        os.makedirs(test_dir, exist_ok=True)
        test_file_path = f"{test_dir}/TEST_RESULTS.md"
        with open(f"{test_file_path}", "w") as file:
            file.write(test_response_text)
        
        print(f"Test results saved to: \n{test_file_path}\n\n")

        return test_response_text

    @property
    def agent(self) -> Agent:
        """Access the underlying phi Agent instance."""
        return self._agent


class DocumentAgent:
    """Agent that creates and updates documentation after an implementation."""

    DEFAULT_MODEL_ID = "qwen3:1.7b"

    def __init__(
        self,
        model_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        base_dir: Optional[Path] = None,
    ):
        self.model_id = model_id or self.DEFAULT_MODEL_ID
        self.workspace_id = workspace_id
        self.base_dir = (base_dir or Path("./").resolve()).resolve()
        self._agent = self._build_agent()

    def _get_instructions(self) -> list[str]:
        today = date.today()
        return [
            "Your role is to create and update documentation based on implementation work that was just completed.",
            "Read the implementation report to understand what was built and which files were created or modified.",
            "Read the relevant source files to capture accurate behavior, APIs, and structure.",
            "Create new documentation (e.g. README) when none exists, or update existing documentation to match the implementation.",
            "Write in clear English. Preserve existing documentation content when updating; only change affected sections.",
            "Only modify documentation files (e.g. README.md, docs/*.md). Do not modify source code.",
            f"The current date is: {today}",
        ]

    def _get_guidelines(self) -> list[str]:
        return [
            "Focus on accuracy: documentation must reflect the actual code and behavior.",
            "Keep documentation concise; avoid redundant or vague descriptions.",
            "When updating existing docs, do not remove unrelated sections.",
        ]

    def _build_agent(self) -> Agent:
        model = Ollama(id=self.model_id)
        return Agent(
            name="Document Agent",
            role="Documentation Agent",
            goal="Create and update documentation after an implementation",
            description="Reads implementation reports and modified files, then creates new documentation or updates existing documentation.",
            model=model,
            tools=[FileToolsWithOptionalListArg(base_dir=self.base_dir)],
            instructions=self._get_instructions(),
            guidelines=self._get_guidelines(),
            markdown=True,
            show_tool_calls=True,
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

        prompt = self._get_prompt(implementation_report)
        response = self._agent.run(prompt, stream=stream)
        response_text = getattr(response, "content", None) or getattr(response, "content_str", None)

        if response_text is None and hasattr(response, "messages") and response.messages:
            last = response.messages[-1]
            response_text = getattr(last, "content", None) or str(last)
        if response_text is None:
            response_text = str(response)

        doc_dir = self.base_dir / "specs" / self.workspace_id
        if self.workspace_id:
            doc_dir.mkdir(parents=True, exist_ok=True)
            doc_file_path = doc_dir / "DOCUMENTATION_SUMMARY.md"
            doc_file_path.write_text(response_text, encoding="utf-8")
            print(f"Documentation summary saved to:\n{doc_file_path}\n")

        return response_text

    @property
    def agent(self) -> Agent:
        """Access the underlying phi Agent instance."""
        return self._agent


def main():
    workspace_id = uuid.uuid4().hex
    code_agent = PlanAgent(workspace_id=workspace_id)
    plan = code_agent.run("create a javascript hello world script to run in a node js environment")

    code_agent = CodeAgent(workspace_id=workspace_id)
    implemented_code = code_agent.run(plan)

    document_agent = DocumentAgent(workspace_id=workspace_id)
    document_agent.run(implemented_code)

    test_agent = TestAgent(workspace_id=workspace_id)
    test_result = test_agent.run(plan, implemented_code)

if __name__ == "__main__":
    main()
