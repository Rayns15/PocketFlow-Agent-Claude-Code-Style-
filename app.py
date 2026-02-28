import streamlit as st
import requests
from flow import build_flow

def check_ollama_status():
    """Pings the local Ollama server to see if it's reachable."""
    try:
        response = requests.get("http://localhost:11434/", timeout=1)
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False

def get_ollama_models():
    """Fetches a list of installed models from the local Ollama instance."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        response.raise_for_status()
        models = response.json().get("models", [])
        return [model["name"] for model in models]
    except Exception:
        return ["gemma"] # Fallback if fetching fails

# Page config
st.set_page_config(page_title="PocketFlow Web Agent", page_icon="🤖")

# --- SIDEBAR WITH STATUS & CONTROLS ---
with st.sidebar:
    st.header("⚙️ Agent Controls")
    
    # 1. System Status
    st.subheader("🔌 System Status")
    server_online = check_ollama_status()
    
    if server_online:
        st.success("🟢 Ollama Server: **Online**")
        available_models = get_ollama_models()
    else:
        st.error("🔴 Ollama Server: **Offline**")
        st.caption("Please run `ollama serve` or open the Ollama app.")
        available_models = ["gemma"] # Fallback

    st.divider()

    # 2. Model Selector
    st.subheader("🧠 Intelligence")
    selected_model = st.selectbox(
        "Select an LLM:", 
        available_models, 
        disabled=not server_online
    )

    st.divider()
    
    # 3. Memory Controls (Split into two buttons)
    st.subheader("🧹 Cleanup")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💬 Clear Chat", use_container_width=True, help="Wipes the visual messages."):
            st.session_state.messages = []
            st.rerun()
            
    with col2:
        if st.button("🧠 Clear History", use_container_width=True, help="Wipes the agent's task memory and approvals."):
            st.session_state.agent_running = False
            st.session_state.shared = {}
            for key in list(st.session_state.keys()):
                if key.startswith("approve_") or key.startswith("deny_"):
                    del st.session_state[key]
            st.rerun()
# --------------------------------------

st.title("🤖 PocketFlow Agent (Claude Code Style)")

# Initialize chat history and state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_running" not in st.session_state:
    st.session_state.agent_running = False
if "shared" not in st.session_state:
    st.session_state.shared = {}

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if server_online:
    if prompt := st.chat_input("Enter your goal (e.g., 'Write a Python script to ping Google')"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Inject the selected model into the shared state!
        st.session_state.shared = {
            "user_goal": prompt,
            "tasks": None,
            "current_index": 0,
            "model": selected_model 
        }
        
        st.session_state.agent_running = True
        st.rerun()
else:
    st.chat_input("Server offline. Please start Ollama first.", disabled=True)

# Agent Execution Block
if st.session_state.agent_running:
    with st.chat_message("assistant"):
        st.session_state.shared["ui"] = st.container()
        
        app_flow = build_flow()
        app_flow.run(st.session_state.shared)
        
        st.session_state.agent_running = False