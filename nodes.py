import os
import time
import json
import requests
import threading
import sys
import itertools
import streamlit as st
from pocketflow import Node

class Spinner:
    """A simple context manager for a terminal loading spinner."""
    def __init__(self, message="Thinking..."):
        self.spinner = itertools.cycle(['-', '\\', '|', '/'])
        self.stop_running = False
        self.message = message
        self.thread = threading.Thread(target=self.spin)

    def spin(self):
        while not self.stop_running:
            sys.stdout.write(f'\r{self.message} {next(self.spinner)}')
            sys.stdout.flush()
            time.sleep(0.1)
        # Clear the spinner line when done
        sys.stdout.write('\r' + ' ' * (len(self.message) + 2) + '\r')
        sys.stdout.flush()

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_running = True
        self.thread.join()

class PlanNode(Node):
    """Takes the user's goal and breaks it down into actionable tasks via Ollama."""
    def prep(self, shared):
        return {
            "goal": shared.get("user_goal"),
            "tasks": shared.get("tasks"), 
            "model": shared.get("model", "gemma"), # Pull the model name, default to gemma
            "ui": shared.get("ui")
        }
        
    def exec(self, prep_data):
        goal = prep_data["goal"]
        tasks = prep_data["tasks"]
        model_name = prep_data["model"]
        ui = prep_data["ui"]
        
        if tasks is not None:
            if ui: ui.info("🔄 Resuming execution from paused state...")
            return tasks

        msg = f"🤔 PLANNING: Asking Ollama ({model_name}) to break down goal -> '{goal}'"
        if ui: ui.info(msg)
        else: print(f"\n{msg}")
        
        prompt = f"""
        You are an AI planner. The user's goal is: "{goal}"
        Break this down into a JSON list of tasks.
        Valid actions are:
        - "mkdir": requires a "target" (directory name)
        - "write_file": requires a "target" (file path) and "content" (string)
        - "run_cmd": requires a "target" (terminal command)
        
        Respond ONLY with a valid JSON array, nothing else. Example:
        [
          {{"action": "mkdir", "target": "my_folder"}},
          {{"action": "write_file", "target": "my_folder/script.py", "content": "print('hello')"}},
          {{"action": "run_cmd", "target": "python my_folder/script.py"}}
        ]
        """
        
        try:
            if not ui:
                with Spinner(f"Waiting for {model_name} to generate plan..."):
                    response = self._fetch_ollama(prompt, model_name)
            else:
                with ui.status(f"Waiting for {model_name} to generate plan...", expanded=True):
                    response = self._fetch_ollama(prompt, model_name)
            
            result_text = response.json().get("response", "[]")
            new_tasks = json.loads(result_text)
            
            if isinstance(new_tasks, dict):
                if "action" in new_tasks:
                    new_tasks = [new_tasks]
                else:
                    extracted_list = []
                    for value in new_tasks.values():
                        if isinstance(value, list):
                            extracted_list = value
                            break
                    new_tasks = extracted_list if extracted_list else [new_tasks]
            
            if not isinstance(new_tasks, list):
                new_tasks = [new_tasks]

            return new_tasks
            
        except Exception as e:
            err_msg = f"❌ Failed to get plan from Ollama: {e}"
            if ui: 
                ui.error(err_msg)
                ui.warning(f"Please ensure your local Ollama server is running and the '{model_name}' model is loaded.")
                st.stop()
            else: 
                print(f"\n{err_msg}")
                sys.exit(1)
            
    def _fetch_ollama(self, prompt, model_name):
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model_name, "prompt": prompt, "stream": False, "format": "json"}
        )
        response.raise_for_status()
        return response
        
    def post(self, shared, prep_res, tasks):
        ui = shared.get("ui")
        shared["tasks"] = tasks
        
        if "current_index" not in shared or shared["current_index"] == 0:
            shared["current_index"] = 0
            if ui:
                ui.success(f"📋 Created a checklist of {len(tasks)} tasks.")
                ui.json(tasks) 
            else:
                print(f"📋 Created a checklist of {len(tasks)} tasks.\n" + "-"*40)
            
        return "next_task"

class ExecuteNode(Node):
    """Acts as a Tool Dispatcher with Human-in-the-Loop safety."""
    def prep(self, shared):
        index = shared["current_index"]
        return {
            "task": shared["tasks"][index],
            "index": index,
            "ui": shared.get("ui")
        }
        
    def exec(self, prep_data):
        task = prep_data["task"]
        index = prep_data["index"]
        ui = prep_data["ui"]
        
        if isinstance(task, str):
            msg = f"📝 NOTE: Skipping text description -> '{task}'"
            if ui: ui.info(msg)
            else: print(f"\n{msg}")
            return "Skipped text description."

        action = task.get("action")
        target = task.get("target")
        
        msg = f"⚙️ **TOOL CALL:** `[{action}]` -> `{target}`"
        if ui: ui.write(msg)
        else: print(f"\n⚙️  TOOL CALL: [{action}] -> '{target}'")
        
        # --- FEATURE 1: HUMAN-IN-THE-LOOP WITH STREAMLIT BUTTONS ---
        if action == "run_cmd":
            if ui:
                # We use the current task index to track approvals
                approval_key = f"approve_{index}"
                denial_key = f"deny_{index}"
                
                # Check if this specific command was already approved/denied
                if st.session_state.get(approval_key):
                    ui.success(f"✅ User approved: `{target}`")
                elif st.session_state.get(denial_key):
                    ui.error(f"❌ User denied: `{target}`")
                    return "Action cancelled by user."
                else:
                    ui.warning(f"⚠️ The agent wants to execute: `{target}`")
                    col1, col2 = ui.columns(2)
                    
                    # Define quick callbacks for our buttons
                    def set_approved(): st.session_state[approval_key] = True
                    def set_denied(): st.session_state[denial_key] = True

                    with col1:
                        st.button("✅ Approve", on_click=set_approved, key=f"btn_app_{index}")
                    with col2:
                        st.button("❌ Deny", on_click=set_denied, key=f"btn_den_{index}")
                        
                    # Stop execution here until the user clicks a button
                    st.stop()
            else:
                print(f"⚠️  WARNING: The agent wants to execute a terminal command.")
                approval = input(f"Allow running `{target}`? (y/n): ")
                if approval.lower() != 'y':
                    return "❌ Action cancelled by user."
        
        time.sleep(1) 
        
        # --- FEATURE 2: REAL FILE SYSTEM TOOLS ---
        try:
            if action == "mkdir":
                os.makedirs(target, exist_ok=True)
                return f"Created directory: {target}"
                
            elif action == "write_file":
                content = task.get("content", "")
                with open(target, "w") as f:
                    f.write(content)
                return f"Wrote {len(content)} bytes to {target}"
                
            elif action == "run_cmd":
                return f"Executed command (Mocked simulation)."
                
            else:
                return f"Unknown tool action: {action}"
                
        except Exception as e:
            return f"❌ Error executing {action}: {str(e)}"
        
    def post(self, shared, prep_res, result):
        ui = shared.get("ui")
        
        if ui:
            ui.write(f"✅ **RESULT:** {result}")
            ui.divider()
        else:
            print(f"✅ RESULT: {result}")
            
        shared["current_index"] += 1
        
        if shared["current_index"] < len(shared["tasks"]):
            return "next_task"
        else:
            return "done"

class SummaryNode(Node):
    """Catches the 'done' state to end the flow cleanly."""
    def prep(self, shared):
        return {
            "tasks": shared["tasks"],
            "ui": shared.get("ui")
        }
        
    def exec(self, prep_data):
        tasks = prep_data["tasks"]
        ui = prep_data["ui"]
        
        msg = f"🎉 All {len(tasks)} operations completed successfully! Returning control."
        
        if ui:
            ui.success(msg)
            ui.balloons() # Added a fun little celebration for the web UI!
        else:
            print("-" * 40)
            print(msg)
            
        return None
        
    def post(self, shared, prep_res, exec_res):
        pass