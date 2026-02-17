from pathlib import Path
import sys

from agents.code import CodeAgent
from agents.files import FilesAgent
from agents.manager import OrchestrationAgent
from agents.web import WebAgent


def parse_prompt_from_args() -> str | None:
    """Return prompt from --prompt=... if present, else None."""
    for arg in sys.argv[1:]:
        if arg.startswith("--prompt="):
            return arg[len("--prompt=") :].strip()
    return None


def main():
    model_id = "llama3.2" # deepseek-r1:1.5b / openhermes / llama3.2
    project_dir = Path(__file__).resolve().parent
    file_agent = FilesAgent(
        model_id=model_id,
        project_dir=project_dir,
    )
    web_agent = WebAgent(
        model_id=model_id,
    )
    code_agent = CodeAgent(
        model_id=model_id,
    )
    manager_agent = OrchestrationAgent(
        model_id=model_id,
        team=[web_agent, code_agent, file_agent],
    )
    prompt = parse_prompt_from_args()
    if prompt is not None:
        manager_agent.run(prompt, stream=True)
        return
    while True:
        prompt = input("Enter your prompt (or 'quit' to exit): ").strip()
        if not prompt or prompt.lower() in ("quit", "exit", "q"):
            break
        manager_agent.run(prompt, stream=True)


if __name__ == "__main__":
    main()
