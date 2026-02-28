import os
import time
import json
import requests
import threading
import sys
import itertools
import streamlit as st
from pocketflow import Node
import shutil
import subprocess
import re

if not os.path.exists("workspace"):
    os.makedirs("workspace")
    gitignore_path = os.path.join("workspace", ".gitignore")
    with open(gitignore_path, "w") as f:
        f.write("*\n!.gitignore\n")

def is_safe_path(target_path, base_dir):
    """Ensures the agent stays within the allowed workspace directory."""
    if not target_path or target_path == "unknown":
        return False
    abs_base = os.path.abspath(base_dir)
    abs_target = os.path.abspath(os.path.join(abs_base, target_path))
    return abs_target.startswith(abs_base)

class PlanNode(Node):
    def prep(self, shared):
        return {
            "goal": shared.get("user_goal"),
            "tasks": shared.get("tasks"), 
            "model": shared.get("model", "gemma"),
            "ui": shared.get("ui"),
            "error_feedback": shared.get("error_feedback")
        }
        
    def _fetch_ollama(self, prompt, model):
        return requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "format": "json"}
        )

    def exec(self, prep_data):
        goal, tasks, model_name, ui, error_feedback = prep_data.values()
        if tasks is not None: return tasks

        if ui:
            status_container = ui.status(f"🤖 **Assistant is thinking ({model_name})...**", expanded=True)
            status_container.write("🧠 Analyzing goal and breaking down steps...")

        # --- Inside PlanNode.exec in nodes.py ---

# Update the prompt to include 'read_file'
        prompt = f"""Goal: {goal}.
        Respond ONLY with a JSON array of task objects. DO NOT use plain strings.
        
        CRITICAL RULES:
        1. If the user asks to *write a script* (bash, python, etc.), use 'write_file' to generate the code. DO NOT execute the actions the script is supposed to do using your own tools.
        2. Always use full paths (e.g., 'folder_name/file.txt').
        
        Example: [{{"action": "mkdir", "target": "my_app"}}, {{"action": "write_file", "target": "my_app/script.sh", "content": "#!/bin/bash\\ncp a b"}}]
        Allowed actions: mkdir, write_file, read_file, run_cmd, copy."""

        # 2. Update the error feedback prompt to remind it of the JSON schema
        if error_feedback:
            prompt = f"""User Goal: {goal}
            The agent encountered an error: {error_feedback}
            
            CRITICAL: You MUST respond ONLY with a JSON array of task objects to fix this.
            Example: [{{"action": "write_file", "target": "fixed_file.txt", "content": "..."}}]
            Allowed actions: mkdir, write_file, read_file, run_cmd, copy.
            
            You can use 'read_file' to inspect the code you wrote before trying to fix it.
            Provide a NEW JSON task list to resolve the issue."""

        try:
            response = self._fetch_ollama(prompt, model_name)
            if ui: status_container.write("📋 Formatting the plan into actionable steps...")
            
            raw_text = response.json().get("response", "[]")
            
            # --- THE ULTIMATE JSON HEALER ---
            decoder = json.JSONDecoder()
            parsed_data = []
            text_to_parse = raw_text
            
            while text_to_parse:
                start_dict = text_to_parse.find('{')
                start_list = text_to_parse.find('[')
                
                starts = [i for i in (start_dict, start_list) if i != -1]
                if not starts:
                    break 
                    
                start_idx = min(starts)
                text_to_parse = text_to_parse[start_idx:]
                
                try:
                    obj, idx = decoder.raw_decode(text_to_parse)
                    parsed_data.append(obj)
                    text_to_parse = text_to_parse[idx:] 
                except json.JSONDecodeError:
                    text_to_parse = text_to_parse[1:]
                    
            # --- THE SCHEMA MAPPER (Fixes the errors in your screenshots) ---
            new_tasks = []
            for item in parsed_data:
                if isinstance(item, list):
                    new_tasks.extend(item)
                elif isinstance(item, dict):
                    if "tasks" in item and isinstance(item["tasks"], list):
                        new_tasks.extend(item["tasks"])
                    # 👇 ADD THIS ELIF BLOCK to catch the "actions" wrapper 👇
                    elif "actions" in item and isinstance(item["actions"], list):
                        new_tasks.extend(item["actions"])
                    elif "action" in item:
                        new_tasks.append(item)
                    else:
                        # Handles hallucinations like: {"mkdir": "folder", "write_file": [...]}
                        for key, val in item.items():
                            if key in ["mkdir", "write_file", "read_file", "run_cmd","copy"]:
                                if isinstance(val, str):
                                    new_tasks.append({"action": key, "target": val})
                                elif isinstance(val, list):
                                    for sub_item in val:
                                        if isinstance(sub_item, str):
                                            new_tasks.append({"action": key, "target": sub_item})
                                        elif isinstance(sub_item, dict):
                                            task_obj = {"action": key}
                                            task_obj["target"] = sub_item.get("target") or sub_item.get("path") or sub_item.get("file")
                                            if "content" in sub_item:
                                                task_obj["content"] = sub_item["content"]
                                            new_tasks.append(task_obj)

            # Map remaining hallucinated keys to 'target'
            final_tasks = []
            for t in new_tasks:
                # NEW: Salvage string commands! (e.g., "mkdir hello_flask")
                if isinstance(t, str):
                    parts = t.split(" ", 1)
                    if len(parts) == 2 and parts[0] in ["mkdir", "write_file", "read_file", "run_cmd","copy"]:
                        final_tasks.append({"action": parts[0], "target": parts[1].strip("'\"")})
                    continue 

                if not isinstance(t, dict): continue

                if "args" in t and isinstance(t["args"], list) and len(t["args"]) > 0:
                    t["target"] = t["args"][0]
                if "path" in t and "target" not in t:
                    t["target"] = t["path"]
                if "file" in t and "target" not in t:
                    t["target"] = t["file"]
                    
                if "action" in t and "target" in t:
                    final_tasks.append(t)
            
            if not final_tasks:
                raise ValueError(f"No valid tasks found. Model output: {raw_text[:100]}...")
                
            if ui:
                status_container.update(label="✅ Plan Generated Successfully!", state="complete", expanded=False)
                
            return final_tasks
            
        except Exception as e:
            err_msg = f"❌ Planning Failed: {str(e)}"
            if ui: 
                status_container.update(label="❌ Planning Failed", state="error")
                ui.error(err_msg)
            if "messages" in st.session_state:
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
            return []

    def post(self, shared, prep_res, tasks):
        if shared.get("tasks") is None:
            shared["tasks"] = tasks
            shared["current_index"] = 0
            if "error_feedback" in shared: del shared["error_feedback"]
            
            ui = shared.get("ui")
            if tasks:
                task_str = "\n".join([f"* **{t.get('action', 'unknown')}**: `{t.get('target', 'unknown')}`" for t in tasks])
                history_msg = f"📋 **Plan Generated:**\n{task_str}"
                
                if "messages" in st.session_state:
                    st.session_state.messages.append({"role": "assistant", "content": history_msg})
                if ui: ui.markdown(history_msg)
            else:
                msg = "❌ No valid tasks were generated by the model."
                if "messages" in st.session_state:
                    st.session_state.messages.append({"role": "assistant", "content": msg})
                if ui: ui.error(msg)
                
        return "next_task"

class ExecuteNode(Node):
    def prep(self, shared):
        tasks = shared.get("tasks", [])
        index = shared.get("current_index", 0)
        
        if not tasks or index >= len(tasks):
            return {"error": "End of plan", "ui": shared.get("ui")}
            
        return {"task": tasks[index], "index": index, "ui": shared.get("ui")}

    def exec(self, prep_data):
        if "error" in prep_data:
            return "Done"
            
        task, index, ui = prep_data.values()
        if isinstance(task, str): return "Skipped text description."
        
        action = task.get("action")
        target = str(task.get("target") or task.get("path", "unknown"))
        
        # --- PATH FIX: Only modify the target if it's a file operation! ---
        # Ensure read_file also stays inside the sandbox
        if action in ["mkdir", "write_file", "read_file","copy"]:
            if not target.startswith("workspace"):
                target = os.path.join("workspace", target)
            
            if not is_safe_path(target, "workspace"):
                 return f"❌ SECURITY ERROR: Access to '{target}' is denied."
        # ------------------------------------------------------------------

        if action == "run_cmd":
            if ui:
                approval_key = f"approve_{index}"
                if not st.session_state.get(approval_key):
                    ui.warning(f"⚠️ **Approval Required**: Run `{target}`?")
                    col1, col2 = ui.columns(2)
                    if col1.button("✅ Approve", key=f"btn_app_{index}"):
                        st.session_state[approval_key] = True
                        st.rerun() 
                    if col2.button("❌ Deny", key=f"btn_deny_{index}"):
                        return "❌ Action denied by user."
                    st.stop() 

        try:
            if action == "mkdir":
                os.makedirs(target, exist_ok=True)
                return f"Created directory: {target}"
            
            elif action == "write_file":
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "w") as f: 
                    f.write(task.get("content", ""))
                return f"Wrote file: {target}"

            # --- NEW TOOL: READ_FILE ---
            elif action == "read_file":
                if not os.path.exists(target):
                    return f"❌ Error: File '{target}' does not exist."
                with open(target, "r") as f:
                    content = f.read()
                return f"Content of {target}:\n\n{content}"
            
            elif action == "copy":
                source = task.get("source")
                if not source:
                    return "❌ Error: 'copy' action requires a 'source' parameter."
                
                # Make sure the source path is safe and inside the workspace
                if not source.startswith("workspace"):
                    source = os.path.join("workspace", source)
                if not is_safe_path(source, "workspace"):
                    return f"❌ SECURITY ERROR: Access to source '{source}' is denied."
                    
                if not os.path.exists(source):
                    return f"❌ Error: Source file '{source}' does not exist."
                    
                # Create the destination directory if it doesn't exist, then copy
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(source, target)
                return f"Copied {source} to {target}"

            elif action == "run_cmd":
                res = subprocess.run(
                    target, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    timeout=30,
                    cwd="workspace"
                )
                return res.stdout if res.returncode == 0 else f"Error: {res.stderr}"
            
            else:
                return f"❌ Error: Unknown action '{action}'. You must only use allowed actions (mkdir, write_file, read_file, run_cmd)."
            
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def post(self, shared, prep_res, result):
        if result == "Done":
            return "done"
            
        if result is None:
            result = "❌ Error: Execution returned no result."

        task = shared["tasks"][shared["current_index"]]
        ui = shared.get("ui")
        
        history_msg = f"⚙️ **Executed:** `{task.get('action')}` on `{task.get('target', task.get('source', 'unknown'))}`\n✅ **Result:**\n```text\n{result}\n```"
        
        if "messages" in st.session_state:
            st.session_state.messages.append({"role": "assistant", "content": history_msg})
        if ui: ui.markdown(history_msg)

        # Did we hit an error?
        if "Error" in str(result) or "❌" in str(result):
            # --- THE CIRCUIT BREAKER ---
            retries = shared.get("retry_count", 0)
            max_retries = 3
            
            if retries >= max_retries:
                # We've tried too many times. Kill the process and move to SummaryNode.
                fatal_msg = f"🛑 **Agent Stopped:** Reached maximum replan attempts ({max_retries}/{max_retries}) without resolving the issue."
                if ui: ui.error(fatal_msg)
                if "messages" in st.session_state:
                    st.session_state.messages.append({"role": "assistant", "content": fatal_msg})
                
                shared["tasks"] = None # Setting this to None forces SummaryNode into its failure state
                shared["error_feedback"] = result
                return "done" 
            
            # If under the limit, increment the counter and replan!
            shared["retry_count"] = retries + 1
            if ui: 
                ui.warning(f"⚠️ Encountered an error. Replanning to fix it... (Attempt {shared['retry_count']}/{max_retries})")
            
            shared["error_feedback"] = result
            shared["tasks"] = None 
            shared["current_index"] = 0 
            return "replan"

        # If the task succeeded, reset the retry counter for the next task!
        shared["retry_count"] = 0 

        shared["current_index"] += 1
        return "next_task" if shared["current_index"] < len(shared["tasks"]) else "done"

class SummaryNode(Node):
    def prep(self, shared): return {"tasks": shared.get("tasks", []), "ui": shared.get("ui"), "error_feedback": shared.get("error_feedback")}
    
    def exec(self, data):
        ui = data["ui"]
        tasks = data["tasks"]
        error_feedback = data.get("error_feedback")
        
        # Logical Fallback: If we failed to get tasks or encountered a fatal error
        if not tasks:
            msg = "⚠️ I couldn't generate a valid technical plan for that request. Could you clarify or break down your goal?"
            if error_feedback:
                msg += f"\n\n**Details:** {error_feedback}"
                
            if ui: ui.warning(msg)
            if "messages" in st.session_state:
                st.session_state.messages.append({"role": "assistant", "content": msg})
            return "Complete"
            
        # Success state
        msg = f"🎉 All {len(tasks)} operations completed successfully!"
        if ui: 
            ui.success(msg)
            ui.balloons()
            
        if "messages" in st.session_state:
            st.session_state.messages.append({"role": "assistant", "content": msg})
        return "Complete"
        
    def post(self, shared, p, e): pass