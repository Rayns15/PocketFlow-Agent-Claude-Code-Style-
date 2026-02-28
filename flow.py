from pocketflow import Flow
from nodes import PlanNode, ExecuteNode, SummaryNode

def build_flow():
    """Constructs and wires the PocketFlow graph."""
    planner = PlanNode()
    executor = ExecuteNode()
    summarizer = SummaryNode()

    # The Graph routing
    planner - "next_task" >> executor
    executor - "next_task" >> executor  
    
    # --- NEW: The Feedback Loop! ---
    executor - "replan" >> planner     
    # -------------------------------
    
    executor - "done" >> summarizer     

    return Flow(start=planner)