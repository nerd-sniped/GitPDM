"""
Example: How UI buttons call actions.

This demonstrates the pattern for Phase 1:
- UI gathers inputs
- Calls action function  
- Displays result
"""

from freecad.gitpdm.actions import (
    create_action_context,
    validate_repo,
    commit_changes,
    push_changes,
)


def example_validate_button_clicked(repo_path: str):
    """
    Example: Validate Repository button handler.
    
    This is how simple button callbacks become:
    1. Gather input (repo_path)
    2. Call action
    3. Display result
    """
    # Create context (typically done once and reused)
    ctx = create_action_context(repo_root=repo_path)
    
    # Call action
    result = validate_repo(ctx, repo_path)
    
    # Display result
    if result.ok:
        print(f"✓ {result.message}")
        print(f"  Repository root: {result.details.get('repo_root')}")
    else:
        print(f"✗ {result.message}")
        print(f"  Error code: {result.error_code}")


def example_commit_button_clicked(repo_path: str, commit_message: str, stage_all: bool):
    """
    Example: Commit button handler.
    
    Shows how to chain actions (commit + push).
    """
    # Create context
    ctx = create_action_context(repo_root=repo_path)
    
    # Commit
    result = commit_changes(ctx, commit_message, stage_all=stage_all)
    
    if not result.ok:
        print(f"✗ Commit failed: {result.message}")
        return
    
    print(f"✓ {result.message}")
    
    # Ask user if they want to push
    user_wants_push = True  # In real UI, this would be a dialog
    
    if user_wants_push:
        push_result = push_changes(ctx)
        
        if push_result.ok:
            print(f"✓ {push_result.message}")
        else:
            print(f"✗ Push failed: {push_result.message}")
            
            # Handle specific errors
            if push_result.error_code == "no_remote":
                print("  Tip: Add a remote first")
            elif push_result.error_code == "push_rejected_behind":
                print("  Tip: Pull changes first, then push")


def example_quick_usage():
    """
    Quick example showing the simplest usage pattern.
    """
    # Initialize once (typically in UI __init__)
    ctx = create_action_context(repo_root="/path/to/repo")
    
    # Later, when button clicked:
    result = commit_changes(ctx, "Updated design", stage_all=True)
    
    # Display in UI status bar or message box
    if result.ok:
        show_success(result.message)  # Your UI function
    else:
        show_error(result.message, result.error_code)  # Your UI function


# Dummy UI functions for example
def show_success(msg):
    print(f"[SUCCESS] {msg}")

def show_error(msg, code):
    print(f"[ERROR] {msg} (code: {code})")


if __name__ == "__main__":
    # Run examples
    print("=== Example 1: Validate Repo ===")
    example_validate_button_clicked("/path/to/repo")
    
    print("\n=== Example 2: Commit + Push ===")
    example_commit_button_clicked("/path/to/repo", "Fixed bug in wheel", stage_all=True)
    
    print("\n=== Example 3: Quick Usage ===")
    example_quick_usage()
