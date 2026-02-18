import uuid
from pathlib import Path
from typing import Optional
from phi.agent import Agent
from phi.model.ollama import Ollama

from test_agent import TestAgent
from implementation_agent import ImplementationAgent
from plan_agent import PlanAgent
from document_agent import DocumentAgent
from base_agent import BaseAgent


class CodeAgent(BaseAgent):
    """Agent that coordinates a team of agents to generate and run code scripts."""

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
            model_id=self.model_id,
            name="Code Coordinator Agent",
            role="Code Coordinator Agent",
            goal="Coordinate a team of agents.",
            description="The Code Coordinator Agent.",
            tools=None,
            workspace_id=self.workspace_id,
            base_dir=self.base_dir,
            command="code_manager",
            team=[
                PlanAgent(workspace_id=self.workspace_id), 
                ImplementationAgent(workspace_id=self.workspace_id), 
                DocumentAgent(workspace_id=self.workspace_id), 
                TestAgent(workspace_id=self.workspace_id)
            ],
        )


def main():
    workspace_id = uuid.uuid4().hex
    # plan_agent = PlanAgent(workspace_id=workspace_id)
    # plan = plan_agent.run("Create a React application using vite and typescript")

    # implementation_agent = ImplementationAgent(workspace_id=workspace_id)
    # implemented_code = implementation_agent.run(plan)

    # document_agent = DocumentAgent(workspace_id=workspace_id)
    # document_agent.run(implemented_code)

    # test_agent = TestAgent(workspace_id=workspace_id)
    # test_result = test_agent.run(plan, implemented_code)

    code_agent = CodeAgent(workspace_id=workspace_id)
    code_agent.run("Create a React application using vite and typescript", stream=True)

if __name__ == "__main__":
    main()
