import streamlit as st
import requests
from flow import build_flow
import os
import shutil

def check_ollama_status():
    try:
        response = requests.get("http://localhost:11434/", timeout=1)
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False

def get_ollama_models():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        response.raise_for_status()
        models = response.json().get("models", [])
        return [model["name"] for model in models]
    except Exception:
        return ["gemma"]

def get_workspace_files(startpath):
    file_list = []
    for root, dirs, files in os.walk(startpath):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, startpath)
            file_list.append((f, full_path, rel_path))
    return file_list

st.set_page_config(page_title="PocketFlow Web Agent", page_icon="🤖")

# Initialize chat history and state early
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_running" not in st.session_state:
    st.session_state.agent_running = False
if "shared" not in st.session_state:
    st.session_state.shared = {"tasks": None, "current_index": 0}

# --- SIDEBAR WITH STATUS & CONTROLS ---
with st.sidebar:
    st.header("⚙️ Agent Controls")
    
    st.subheader("📂 Workspace Explorer")
    if not os.path.exists("workspace"):
        os.makedirs("workspace")

    files = get_workspace_files("workspace")
    if not files:
        st.caption("Workspace is currently empty.")
    else:
        with st.expander("Show Files & Downloads", expanded=True):
            for filename, full_path, rel_path in files:
                st.markdown(f"📄 {rel_path}")
                with open(full_path, "rb") as f:
                    st.download_button("💾 Download", f, file_name=filename, key=f"dl_{rel_path}")

    with st.expander("🗑️ Advanced Cleanup"):
        if st.button("Delete All Workspace Files", use_container_width=True):
            if os.path.exists("workspace"):
                # Instead of deleting the folder, we delete its contents
                for filename in os.listdir("workspace"):
                    file_path = os.path.join("workspace", filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path) # Delete file or link
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path, ignore_errors=True) # Delete sub-directory
                    except Exception as e:
                        st.error(f"Failed to delete {file_path}. Reason: {e}")
                
                # Re-ensure .gitignore exists so the workspace stays clean in Git
                gitignore_path = os.path.join("workspace", ".gitignore")
                with open(gitignore_path, "w") as f:
                    f.write("*\n!.gitignore\n")
            st.rerun()

    st.subheader("🔌 System Status")
    server_online = check_ollama_status()
    
    if server_online:
        st.success("🟢 Ollama Server: **Online**")
        available_models = get_ollama_models()
    else:
        st.error("🔴 Ollama Server: **Offline**")
        available_models = ["gemma"]

    st.divider()
    st.subheader("🧠 Intelligence")
    selected_model = st.selectbox("Select an LLM:", available_models, disabled=not server_online)

    st.divider()
    st.subheader("🧹 Cleanup")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💬 Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
            
    with col2:
        if st.button("🧠 Clear History", use_container_width=True):
            st.session_state.agent_running = False
            st.session_state.shared = {"tasks": None, "current_index": 0}
            for key in list(st.session_state.keys()):
                if key.startswith("approve_") or key.startswith("deny_"):
                    del st.session_state[key]
            st.rerun()

# --- MAIN UI ---
st.title("🤖 PocketFlow Agent (Claude Code Style)")

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if server_online:
    if prompt := st.chat_input("Enter your goal (e.g., 'Write a Python script to ping Google')"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Reset the shared state for a fresh run
        st.session_state.shared.update({
            "user_goal": prompt,
            "tasks": None,
            "current_index": 0,
            "model": selected_model,
            "error_feedback": None 
        })
        
        st.session_state.agent_running = True
        st.rerun()
else:
    st.chat_input("Server offline. Please start Ollama first.", disabled=True)

# --- Final Render Logic ---
if st.session_state.agent_running:
    with st.chat_message("assistant"):
        ui_block = st.container()
        st.session_state.shared["ui"] = ui_block
        
        try:
            app_flow = build_flow()
            app_flow.run(st.session_state.shared)
            
            # Flow finished natively! Clean up UI and lock into permanent history.
            st.session_state.agent_running = False
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Agent Error: {e}")
            st.session_state.agent_running = False