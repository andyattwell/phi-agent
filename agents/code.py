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
            "Generate code in the requested language to fulfill the user's request.",
            "When the user asks for a script or code: produce complete, runnable code. Use the appropriate tool to save and run it when run_code is enabled.",
            "Prefer clear, readable code. Add minimal comments only where they help understanding.",
            "If the user asks to run or execute code, use run_python_code or save_to_file_and_run as appropriate. Install required packages with pip_install_package when needed and pip_install is enabled.",
            "When returning code in your response, use markdown code blocks with the correct language (e.g. ```python). If the user asked for 'only code', omit long explanations and return the code first.",
            "Use the minimum number of tool calls required. Do not run code unnecessarily when the user only asked for the code.",
            "Use the shell tool to run code in the requested language.",
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

    def run(self, prompt: str, stream: bool = True) -> None:
        """Run the agent with the given prompt and print the response."""
        # self._agent.print_response(prompt, stream=stream)

        print(f"Running plan for prompt: {prompt}")
        cmds_path = f"{self.base_dir}/agents/commands"

        with open(f"{cmds_path}/plan.md", "r") as file:
            plan_prompt = file.read()
        plan_prompt = plan_prompt.replace("{{prompt}}", prompt)
        plan_prompt = plan_prompt.replace("{{base_url}}", str(self.base_dir))
        plan_response = self._agent.run(plan_prompt, stream=False)
        plan_response_text = getattr(plan_response, "content", None) or getattr(plan_response, "content_str", None)
        if plan_response_text is None and hasattr(plan_response, "messages") and plan_response.messages:
            last = plan_response.messages[-1]
            plan_response_text = getattr(last, "content", None) or str(last)
        if plan_response_text is None:
            plan_response_text = str(plan_response)
        
        print(f"Plan: \n\n{plan_response_text}\n\n")
        return 

        print(f"Writing code for prompt")
        with open(f"{cmds_path}/implement.md", "r") as file:
            implement_prompt = file.read()
        implement_prompt = implement_prompt.replace("{{implementation_plan}}", plan_response_text)
        implement_prompt = implement_prompt.replace("{{base_dir}}", str(self.base_dir))
        implement_response = self._agent.run(implement_prompt, stream=False)
        implement_response_text = getattr(implement_response, "content", None) or getattr(implement_response, "content_str", None)
        if implement_response_text is None and hasattr(implement_response, "messages") and implement_response.messages:
            last = implement_response.messages[-1]
            implement_response_text = getattr(last, "content", None) or str(last)
        if implement_response_text is None:
            implement_response_text = str(implement_response)
        
        print(f"Files: \n\n{implement_response_text}\n\n")

        print(f"Running tests")
        with open(f"{cmds_path}/test.md", "r") as file:
            test_prompt = file.read()
        test_prompt = test_prompt.replace("{{implement_response}}", implement_response_text)
        test_prompt = test_prompt.replace("{{implementation_plan}}", plan_response_text)
        test_prompt = test_prompt.replace("{{prompt}}", prompt)
        test_prompt = test_prompt.replace("{{base_dir}}", str(self.base_dir))
        test_response = self._agent.run(test_prompt, stream=False)
        test_response_text = getattr(test_response, "content", None) or getattr(test_response, "content_str", None)
        if test_response_text is None and hasattr(test_response, "messages") and test_response.messages:
            last = test_response.messages[-1]
            test_response_text = getattr(last, "content", None) or str(last)
        if test_response_text is None:
            test_response_text = str(test_response)
        print(f"Testing: \n\n{test_response_text}\n\n")


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
        cmds_path = f"{self.base_dir}/agents/commands"
        instructions = []
        with open(f"{cmds_path}/agent.md", "r") as file:
            agent_prompt = file.read()
        instructions.extend(agent_prompt.split("\n"))

        with open(f"{cmds_path}/plan-instructions.md", "r") as file:
            plan_prompt = file.read()
        plan_prompt = plan_prompt.replace("{{base_dir}}", str(self.base_dir))
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
        print(f"Instructions: \n\n{self._get_instructions()}\n\n")
        print(f"Guidelines: \n\n{self._get_guidelines()}\n\n")
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

    def run(self, prompt: str, stream: bool = True) -> str:
        """Run the agent with the given prompt and print the response."""
        # self._agent.print_response(prompt, stream=stream)

        print(f"Running plan for prompt: {prompt}")

        cmds_path = f"{self.base_dir}/agents/commands"

        with open(f"{cmds_path}/plan.md", "r") as file:
            plan_prompt = file.read()
        plan_prompt = plan_prompt.replace("{{prompt}}", prompt)
        plan_prompt = plan_prompt.replace("{{base_dir}}", str(self.base_dir))
        plan_response = self._agent.run(plan_prompt, stream=False)
        plan_response_text = getattr(plan_response, "content", None) or getattr(plan_response, "content_str", None)
        if plan_response_text is None and hasattr(plan_response, "messages") and plan_response.messages:
            last = plan_response.messages[-1]
            plan_response_text = getattr(last, "content", None) or str(last)
        if plan_response_text is None:
            plan_response_text = str(plan_response)
        
        print(f"Plan: \n\n{plan_response_text}\n\n")

        # save the plan to a file
        random_name = uuid.uuid4().hex
        os.makedirs(f"{self.base_dir}/specs/{random_name}", exist_ok=True)
        plan_file_path = f"{self.base_dir}/specs/{random_name}/IMPLEMENTATION_PLAN.md"
        with open(f"{plan_file_path}", "w") as file:
            file.write(plan_response_text)
        print(f"Plan saved to {plan_file_path}")
        return plan_file_path


    @property
    def agent(self) -> Agent:
        """Access the underlying phi Agent instance."""
        return self._agent


def main():
    code_agent = PlanAgent()
    plan = code_agent.run("create a javascript hello world script to run in a node js environment")
    print(f"Plan: \n\n{plan}\n\n")

    # code_agent = CodeAgent()
    # code_agent.run("create a javascript hello world script to run in a node js environment")

if __name__ == "__main__":
    main()
