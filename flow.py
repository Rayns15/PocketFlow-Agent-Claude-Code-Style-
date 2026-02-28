from pocketflow import Flow
from nodes import PlanNode, ExecuteNode, SummaryNode

def build_flow():
    """Constructs and wires the PocketFlow graph."""
    # 1. Initialize Nodes
    planner = PlanNode()
    executor = ExecuteNode()
    summarizer = SummaryNode()

    # 2. Define the Graph routing
    planner - "next_task" >> executor
    executor - "next_task" >> executor  # Loop back to itself
    executor - "done" >> summarizer     # Catch the finish line!

    # 3. Return the compiled Flow
    return Flow(start=planner)