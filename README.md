# phi-agent

A multi-agent assistant that runs entirely on local models. A manager agent receives a prompt and delegates it to a team of specialist agents, all backed by a model served with llama.cpp.

Built with [Phidata](https://github.com/phidatahq/phidata). It is an experiment in how far small local models can go with agentic, tool-using workflows.

## Agents

| Agent | Role |
| --- | --- |
| **Manager** (`agents/manager.py`) | Coordinates the team: delegates each task to the right specialist and summarizes the results. |
| **Web** (`agents/web.py`) | Searches the web with DuckDuckGo and cites its sources. |
| **Code** (`agents/code_agent.py`) | Coordinates coding work, starting with a planning agent. Implementation, documentation and test agents are in progress. |
| **Files** (`agents/files.py`) | Lists, reads, creates and edits files inside the project folder. |
| **Validation** (`agents/validation.py`) | Uses read-only file access to check whether the other agents fulfilled the request, and reports FULFILLED, PARTIAL or NOT FULFILLED. |

The prompts that guide the coding agents live in `agents/commands/`.

## llama.cpp adapter

Phidata supports Ollama but not llama.cpp's `llama-server`. `agents/llama_cpp_phi.py` subclasses Phidata's Ollama model so responses, streaming and tool calls behave the same, while the requests go to llama-server's OpenAI-compatible API.

## Usage

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
# with llama-server already running; both can also go in a .env file
export LLAMA_SERVER_URL=http://localhost:8080
export LLAMA_MODEL_PATH=/path/to/model.gguf
uv run main.py --prompt="Find the latest Node.js LTS version and save it to notes.md"
```

Without `--prompt`, it starts an interactive loop.

## Status

Work in progress: the coding team is being expanded and some agents are still commented out.
