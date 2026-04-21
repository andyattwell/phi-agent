from typing import Optional
from pathlib import Path

from agents.files import FileToolsWithOptionalListArg
from agents.base_agent import BaseAgent

class PlanAgent(BaseAgent):
    """Agent that generates implementation plans."""

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
        super().__init__(
            model_path=self.model_path,
            model_id=self.model_id,
            name="Plan Agent", 
            role="Plan Agent", 
            goal=f"Generate a software implementation plan.", 
            description="The Plan Agent is responsible for generating a software implementation plan.", 
            tools=[FileToolsWithOptionalListArg(base_dir=self.base_dir)],
            workspace_id=self.workspace_id,
            base_dir=self.base_dir,
            command="plan",
        )

