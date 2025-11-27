"""
Verification script for the history parsing fix.
"""
import sys

def verify_fix():
    print("🧪 Verifying history parsing fix...")
    
    # Test cases that previously failed or might fail
    test_cases = [
        ("Standard list", [["Hello", "Hi"]]),
        ("Tuple list", [("Hello", "Hi")]),
        ("Dict list", [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}]),
        ("Single item list (Edge case)", [["Just user msg"]]),
        ("Mixed garbage (Should skip)", ["Invalid string", 123, None, [], {}])
    ]
    
    for name, history in test_cases:
        print(f"\nTesting: {name}")
        print(f"Input: {history}")
        
        parsed_messages = []
        
        # --- THE FIX LOGIC START ---
        for i, entry in enumerate(history):
            try:
                user_msg = None
                assistant_msg = None
                
                # Handle list/tuple format: [user, bot] or (user, bot)
                if isinstance(entry, (list, tuple)):
                    if len(entry) >= 2:
                        user_msg = entry[0]
                        assistant_msg = entry[1]
                    elif len(entry) == 1:
                        user_msg = entry[0]
                
                # Handle dictionary format (OpenAI style)
                elif isinstance(entry, dict):
                    if "role" in entry and "content" in entry:
                        if entry["role"] == "user":
                            user_msg = entry["content"]
                        elif entry["role"] == "assistant":
                            assistant_msg = entry["content"]
                
                # Add to memory if valid
                if user_msg:
                    parsed_messages.append(f"User: {user_msg}")
                if assistant_msg:
                    parsed_messages.append(f"AI: {assistant_msg}")
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not parse history entry {i}: {entry} - {e}")
                continue
        # --- THE FIX LOGIC END ---
        
        print(f"✅ Parsed: {parsed_messages}")

if __name__ == "__main__":
    verify_fix()
