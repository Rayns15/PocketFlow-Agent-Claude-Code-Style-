# 🤖 PocketFlow Agent (Claude Code Style)

A local, autonomous AI agent built with the **PocketFlow** framework, powered by **Ollama**, and featuring a beautiful **Streamlit** Web UI. 

This agent takes high-level user goals, breaks them down into actionable steps, and executes them on your local machine using actual file system tools. It features a "Human-in-the-Loop" safeguard that pauses execution to ask for your permission before running any terminal commands, as well as a self-healing ReAct loop to fix its own errors.

![Claude Code Style UI](Claude%20Code%20Style.jpg)

## ✨ Advanced Features

* **🧠 Local AI Powered:** Connects directly to your local [Ollama](https://ollama.com/) instance for completely private, offline task execution.
* **🔀 Dynamic Model Selection:** Automatically detects installed Ollama models (e.g., `gemma`, `llama3`, `mistral`) and lets you swap between them on the fly.
* **🔄 Self-Healing (ReAct Loop):** If a terminal command fails (e.g., a missing pip package), the agent catches the error, sends the logs back to the LLM, and automatically generates a new plan to fix the issue.
* **🛡️ Secure Sandboxing:** All file operations are strictly confined to an auto-generated `workspace/` folder to prevent accidental modifications to your host system. 
* **🛑 Human-in-the-Loop:** Automatically halts and prompts for User Approval (✅ / ❌) directly in the UI before executing potentially dangerous terminal commands.
* **📂 Live Workspace Explorer:** A sidebar utility that tracks the files your agent creates in real-time, complete with instant Download buttons.
* **🩹 The "JSON Healer":** Features a custom, highly-resilient JSON extraction engine that intercepts chatty LLMs, maps hallucinated keys, injects missing array brackets, and guarantees stable execution regardless of how the model formats its output.

## 🚀 Prerequisites

1. **Python 3.8+**
2. **Ollama:** You must have [Ollama](https://ollama.com/) installed and running on your machine.
3. **An LLM Model:** Pull at least one model via Ollama (e.g., `ollama pull gemma`).

## 🛠️ Installation

1. Clone this repository to your local machine.
2. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt

## 🎮 How to Run

Start the interactive Streamlit dashboard. This provides a chat interface, real-time agent status indicators, and interactive approval buttons.

```bash
streamlit run app.py

```

*Note: The first time you run the app, it will automatically generate a `workspace/` directory complete with a `.gitignore` file to ensure the agent's generated code doesn't clutter your repository.*

## 🏗️ Architecture Under the Hood

The agent's logic is powered by a 3-node **PocketFlow** graph:

1. **PlanNode:** Receives the user goal, queries Ollama with strict system prompts, and extracts an actionable JSON array of tool calls. If an error occurred in a previous step, it dynamically adjusts its prompt to recover.
2. **ExecuteNode:** Acts as the Tool Dispatcher.
* Validates paths against the Sandbox.
* Auto-creates missing parent directories.
* Prompts the user via Streamlit for `run_cmd` execution.
* Routes failures back to the `PlanNode` for the ReAct loop.


3. **SummaryNode:** Catches the completion state, logs the permanent history, and cleans up the flow.

## 🧰 Available Agent Tools

The agent is currently equipped with three core capabilities:

* `mkdir`: Creates directories inside the workspace.
* `write_file`: Writes code, configuration files, and scripts to the workspace.
* `run_cmd`: Executes terminal commands (e.g., `pip install`, `python script.py`) natively inside the workspace directory.

## 🧹 Memory Management

The Web UI leverages `st.session_state` to remember chat history, agent tasks, and tool approvals across re-runs. You can clear the visual chat or wipe the agent's entire short-term memory using the dedicated cleanup buttons in the sidebar.

```

***

### What's Next?
You now have a fully functional foundation! If you ever want to expand this project, you could easily add more tools to the `ExecuteNode`—such as a `read_file` tool (so the agent can read existing code and edit it) or a `web_search` tool! 

Would you like me to help you brainstorm how to add a `read_file` tool to your agent's repertoire next?

```

![Style](https://github.com/Rayns15/PocketFlow-Agent-Claude-Code-Style-/blob/262631ced90cd6f711b6422dc29a35f2cc8c2d4e/Claude%20Code%20Style.jpg)