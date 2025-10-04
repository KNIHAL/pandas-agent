import os
import getpass
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

load_dotenv()

# --- API Key setup ---
if not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter API key for Google Gemini: ")

llm = LLM(
    api_key=os.getenv("GOOGLE_API_KEY"),
    model="gemini/gemini-2.0-flash",
    temperature=0.1,
)

# --- MCP Server adapter setup ---
server_params = StdioServerParameters(
    command="python3",
    args=["./server.py"],  # path to your MCP server entrypoint
    env={"UV_PYTHON": "3.12", **os.environ},  # propagate env variables + python version
)

with MCPServerAdapter(server_params) as tools:
    print("Available MCP tools:", [tool.name for tool in tools])

    # You could optionally add a custom save tool here if framework allows
    # e.g. tools.add_tool(MySaveTool(...))

    # --- Define the Pandas agent ---
    pandas_agent = Agent(
        role="Data Cleaning Agent",
        goal="Load, clean, analyze, and save dataset provided by user.",
        backstory=(
            "You are a data cleaning expert. "
            "Your capabilities include reading user data files (CSV, Excel), cleaning nulls, duplicates, outliers, "
            "answering user queries about the data, and saving the cleaned version in a designated folder."
        ),
        tools=tools,
        reasoning=True,
        verbose=True,
        allow_code_execution=True,
    )

    processing_task = Task(
        description=(
            "User will supply file path to a dataset. "
            "You must: 1) load the dataset from that path, 2) clean the data (remove nulls, duplicates, treat outliers), "
            "3) answer user queries about the cleaned data, and 4) save the cleaned dataset in a `cleaned/` folder. "
            "Return summary of cleaning steps, path of cleaned file, and any answers."
        ),
        expected_output="A structured response including cleaned data summary + cleaned file path + answers to queries.",
        agent=pandas_agent,
        markdown=True,
    )

    data_crew = Crew(
        agents=[pandas_agent],
        tasks=[processing_task],
        verbose=True,
        process=Process.sequential,
    )

def clean_data():
    file_path = input("Enter path to your data file (CSV / Excel): ").strip()
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return
    # Create folder for cleaned outputs
    cleaned_folder = "cleaned"
    os.makedirs(cleaned_folder, exist_ok=True)

    # Prepare input dict, you can pass more inputs if needed
    result = data_crew.kickoff(inputs={"file_path": file_path})
    
    # The agent’s result should include where the cleaned file is saved
    print("=== Agent Output ===")
    print(result)

if __name__ == "__main__":
    clean_data()
