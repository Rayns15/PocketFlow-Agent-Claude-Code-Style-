# 🤖 PocketFlow Agent (Claude Code Style)

A local, autonomous AI agent built with the **PocketFlow** framework, powered by **Ollama**, and featuring a beautiful **Streamlit** Web UI. 

This agent takes high-level user goals, breaks them down into actionable steps, and executes them on your local machine using actual file system tools. It features a "Human-in-the-Loop" safeguard that pauses execution to ask for your permission before running any terminal commands.

## ✨ Features

* **🧠 Local AI Powered:** Connects directly to your local [Ollama](https://ollama.com/) instance.
* **🔀 Dynamic Model Selection:** Automatically detects installed Ollama models (e.g., `gemma`, `llama3`, `mistral`) and lets you swap between them on the fly.
* **🛡️ Human-in-the-Loop:** Automatically halts and prompts for User Approval (✅ / ❌) before executing potentially dangerous `run_cmd` tasks.
* **🛠️ Real File System Tools:** Capable of creating directories (`mkdir`) and writing scripts/files (`write_file`) to your local disk.
* **💻 Dual Interfaces:** Run the agent visually in your browser via Streamlit, or in your terminal via the CLI.
* **🧠 Persistent Memory:** The Web UI leverages `st.session_state` to remember chat history, agent tasks, and tool approvals across re-runs.

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

You can run the PocketFlow Agent in two different ways:

### Option 1: The Web UI (Recommended)

Launch the interactive Streamlit dashboard. This provides a chat interface, system status indicators, model selection, and interactive approval buttons.

```bash
streamlit run app.py

```

### Option 2: The Terminal CLI

Run the agent in a lightweight terminal interface. Uses text-based loading spinners and `(y/n)` input prompts for human-in-the-loop approvals.

```bash
python main.py

```

## 🏗️ Architecture

The agent's logic is defined in `nodes.py` and routed in `flow.py` using a 3-node graph:

* **PlanNode:** Receives the user goal, queries Ollama to break it down, and outputs a strict JSON array of tool calls.
* **ExecuteNode:** Acts as a tool dispatcher. Loops through the planned tasks. If the task is safe (`mkdir`, `write_file`), it executes it. If it is a terminal command (`run_cmd`), it halts and waits for user approval.
* **SummaryNode:** Catches the completion state and cleans up the flow.

```

***

Now your project is officially documented! 

Picking up right where your copy-paste left off—would you like me to show you how to upgrade the `run_cmd` tool using Python's `subprocess` module so it actually executes those terminal commands on your machine instead of just printing a mocked simulation message?

```

![Style](hhttps://github.com/Rayns15/PocketFlow-Agent-Claude-Code-Style-/blob/262631ced90cd6f711b6422dc29a35f2cc8c2d4e/Claude%20Code%20Style.jpg)