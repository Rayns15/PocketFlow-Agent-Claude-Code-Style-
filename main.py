from flow import build_flow

def main():
    print("🤖 Welcome to the PocketFlow CLI Assistant (Claude Code Clone)")
    
    # 1. Ask the user for their goal dynamically
    user_goal = input("Enter your goal: ")
    
    # Fallback just in case they press enter without typing anything
    if not user_goal.strip():
        user_goal = "Create a Python script that scrapes Hacker News"
        print(f"No input provided. Using default: {user_goal}")

    # 2. Construct the graph
    app_flow = build_flow()
    
    # 3. Define the starting state
    shared_state = {
        "user_goal": user_goal
    }
    
    # 4. Execute the flow
    app_flow.run(shared_state)

if __name__ == "__main__":
    main()