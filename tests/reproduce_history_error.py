"""
Reproduction script for "too many values to unpack" error in chatbot history.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def simulate_error():
    print("🧪 Simulating Gradio history error...")
    
    # Scenario 1: Standard list of lists (Should work)
    history_standard = [["Hello", "Hi there"], ["How are you?", "I'm good"]]
    print(f"\n1. Testing standard history: {history_standard}")
    try:
        for user_msg, assistant_msg in history_standard:
            pass
        print("✅ Standard history unpacked successfully")
    except Exception as e:
        print(f"❌ Standard history failed: {e}")

    # Scenario 2: Gradio 4.x sometimes sends tuples (Should work)
    history_tuples = [("Hello", "Hi there"), ("How are you?", "I'm good")]
    print(f"\n2. Testing tuple history: {history_tuples}")
    try:
        for user_msg, assistant_msg in history_tuples:
            pass
        print("✅ Tuple history unpacked successfully")
    except Exception as e:
        print(f"❌ Tuple history failed: {e}")

    # Scenario 3: OpenAI style dicts (Common in newer Gradio versions)
    history_dicts = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}]
    print(f"\n3. Testing dict history: {history_dicts}")
    try:
        for user_msg, assistant_msg in history_dicts:
            pass
        print("✅ Dict history unpacked successfully")
    except Exception as e:
        print(f"❌ Dict history failed: {e}")  # Expecting this to fail

    # Scenario 4: Single item (Edge case)
    history_single = ["Just a string"]
    print(f"\n4. Testing single item history: {history_single}")
    try:
        for user_msg, assistant_msg in history_single:
            pass
        print("✅ Single item unpacked successfully")
    except Exception as e:
        print(f"❌ Single item failed: {e}")

if __name__ == "__main__":
    simulate_error()
