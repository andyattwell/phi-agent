import uuid
from pathlib import Path
from typing import Optional
from agents.base_agent import BaseAgent
from agents.plan_agent import PlanAgent


class CodeAgent(BaseAgent):
    """Agent that coordinates a team of agents to generate and run code scripts."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        base_dir: Optional[Path] = None,
    ):
        self.model_path = model_path
        self.model_id = model_id
        self.workspace_id = workspace_id or "default"
        self.base_dir = (base_dir or Path("./").resolve()).resolve()
        plan_agent = PlanAgent(
            model_path=self.model_path,
            model_id=self.model_id,
            workspace_id=self.workspace_id,
        )
        super().__init__(
            model_path=self.model_path,
            model_id=self.model_id,
            name="Code Coordinator Agent",
            role="Code Coordinator Agent",
            goal="Delegate tasks to the appropriate agents.",
            description="The Code Coordinator Agent is responsible for delegating tasks to the appropriate agents.",
            tools=None,
            workspace_id=self.workspace_id,
            base_dir=self.base_dir,
            command="code_manager",
            team=[
                plan_agent.agent, 
                # ImplementationAgent(workspace_id=self.workspace_id), 
                # DocumentAgent(workspace_id=self.workspace_id), 
                # TestAgent(workspace_id=self.workspace_id)
            ],
        )


def main():
    workspace_id = uuid.uuid4().hex
    code_agent = CodeAgent(workspace_id=workspace_id)
    code_agent.run("Create a React application using vite and typescript", stream=True)

if __name__ == "__main__":
    main()
