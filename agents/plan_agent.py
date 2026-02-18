
from typing import Optional
from pathlib import Path
from phi.agent import Agent
from phi.model.ollama import Ollama
from tools.duckduckgo import DuckDuckGo
from files import FileToolsWithOptionalListArg
from datetime import date
from base_agent import BaseAgent

class PlanAgent(BaseAgent):
    """Agent that generates implementation plans."""


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
            name="Plan Agent", 
            role="Plan Agent", 
            goal=f"Generate a software implementation plan and save it as `specs/{self.workspace_id}/PLAN.md`", 
            description="You are an expert software developer. You are given a user prompt and you need to generate a step by step implementation plan to fulfill the user request.", 
            tools=[DuckDuckGo(), FileToolsWithOptionalListArg(base_dir=self.base_dir)],
            workspace_id=self.workspace_id,
            base_dir=self.base_dir,
        )

