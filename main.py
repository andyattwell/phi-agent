from pathlib import Path
import os
import sys

from dotenv import load_dotenv

from agents.code_agent import CodeAgent
from agents.files import FilesAgent
from agents.manager import OrchestrationAgent
from agents.validation import ValidationAgent
from agents.web import WebAgent


def parse_prompt_from_args() -> str | None:
    """Return prompt from --prompt=... if present, else None."""
    for arg in sys.argv[1:]:
        if arg.startswith("--prompt="):
            return arg[len("--prompt=") :].strip()
    return None


def main():
    load_dotenv()
    model_path = os.environ.get("LLAMA_MODEL_PATH")
    project_dir = Path(__file__).resolve().parent
    file_agent = FilesAgent(
        model_path=model_path,
        project_dir=project_dir,
    )
    web_agent = WebAgent(
        model_path=model_path,
    )
    code_agent = CodeAgent(
        model_path=model_path,
        base_dir=project_dir
    )
    validation_agent = ValidationAgent(
        model_path=model_path,
        project_dir=project_dir,
    )
    manager_agent = OrchestrationAgent(
        model_path=model_path,
        team=[web_agent, code_agent, file_agent, validation_agent],
    )

    prompt = parse_prompt_from_args()
    if prompt is not None:
        manager_agent.run(prompt, stream=True)
    while True:
        prompt = input("Enter your prompt (or 'quit' to exit): ").strip()
        if not prompt or prompt.lower() in ("quit", "exit", "q"):
            break
        manager_agent.run(prompt, stream=True)


if __name__ == "__main__":
    main()
