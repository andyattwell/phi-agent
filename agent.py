import json
import sys
from pathlib import Path
from typing import Optional
from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.file import FileTools
# from phi.tools.yfinance import YFinanceTools
from phi.utils.log import logger


class FileToolsWithOptionalListArg(FileTools):
    """FileTools with list_files accepting optional file_name so the model can call list_files(file_name='x') without validation error."""

    def list_files(self, file_name: Optional[str] = None) -> str:
        """Returns a list of files in the base directory. file_name is optional and ignored; use read_file to read a specific file."""
        try:
            logger.info(f"Listing files in: {self.base_dir}")
            return json.dumps([str(p) for p in self.base_dir.iterdir()], indent=4)
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return f"Error listing files: {e}"
# from phi.embedder.ollama import OllamaEmbedder
# from phi.knowledge.pdf import PDFUrlKnowledgeBase
# from phi.vectordb.lancedb import LanceDb, SearchType

def main():

    web_instructions = 'Always include sources'
    # finance_instructions = 'Use tables to display data'
    project_dir = Path(__file__).resolve().parent
    files_instructions = (
        "Only access files inside of the project folder. "
        "When asked to edit files, keep the original content and add the new content unless asked to replace it. Don\'t create new files, edit the original file. "
        "When asked to create or write a file, you MUST call the save_file tool with the given file name and contents; "
        "do not respond with only text. After saving, return the file path."
    )
    code_instructions = 'Return only code, don\'t explain anything'

    model_id = "llama3.2" # deepseek-r1:1.5b / openhermes / llama3.2
    model = Ollama(id=model_id)
    # embeddings = OllamaEmbedder().get_embedding("The quick brown fox jumps over the lazy dog.")

    # knowledge_base = PDFUrlKnowledgeBase(
    #     urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    #     vector_db=LanceDb(
    #         table_name="recipes",
    #         uri="tmp/lancedb",
    #         search_type=SearchType.vector,
    #         embedder=OllamaEmbedder(),
    #     ),
    # )
    # knowledge_base.load()

    # rag_agent = Agent(
    #     name="Rag Agent",
    #     role="Find information in knowledge base",
    #     model=model,
    #     knowledge=knowledge_base,
    #     show_tool_calls=True,
    #     markdown=True,
    # )

    code_agent = Agent(
        name="Coder Agent",
        role="Generate code scripts",
        model=model,
        markdown=True,
        pip_install=True,
        show_tool_calls=True,
        instructions= code_instructions
    )

    file_agent = Agent(
        name="Files Agent",
        role="Create, update, delete, find files in the project folder",
        model=model,
        tools=[FileToolsWithOptionalListArg(base_dir=project_dir)],
        instructions=[files_instructions],
        markdown=True,
        show_tool_calls=True,
    )

    web_agent = Agent(
        name="Web Agent",
        role="Search the web for information",
        model=model,
        tools=[DuckDuckGo()],
        instructions=[web_instructions],
        show_tool_calls=True,
        markdown=True,
    )

    # finance_agent = Agent(
    #     name="Finance Agent",
    #     role="Get financial data",
    #     model=model,
    #     tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)],
    #     instructions=[finance_instructions],
    #     show_tool_calls=True,
    #     markdown=True,
    # )

    agent_team = Agent(
        model=model,
        team=[web_agent, code_agent, file_agent],
        instructions=[
            web_instructions,
            code_instructions,
            files_instructions,
            "For file operations (create, edit, delete, read files) you MUST call the transfer_task_to_files_agent tool; never output tool-call JSON as text.",
        ],
        show_tool_calls=True,
        markdown=True,
    )
    # prompt = "Create a text file with the content 'Hello world'. Save it with the name 'test.txt'"
    prompt = "edit the file test.txt. Add a the title 'This is a test' and at the bottom of the file the current date"
    agent_team.print_response(prompt, stream=True)

    sys.exit(0)



if __name__ == "__main__":
    main()
