import gradio as gr
from gradio import ChatMessage
from openai import OpenAI
import os
from dotenv import load_dotenv # <-- NEW IMPORT
from typing import Iterator, List, Dict, Any, Tuple

# --- API Configuration ---

# Load environment variables from the .env file
# This is the correct way to handle keys locally!
load_dotenv() 

# Retrieve the OpenAI API key from the environment
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialization logic remains the same, but now pulls from the environment
client = None
MODEL_NAME = "gpt-3.5-turbo"

if OPENAI_API_KEY:
    try:
        # Initialize the OpenAI client
        client = OpenAI(api_key=OPENAI_API_KEY)
        print("OpenAI client initialized successfully from .env key.")
    except Exception as e:
        print(f"Warning: Could not initialize OpenAI client despite finding key. Error: {e}")
else:
    print("Warning: OPENAI_API_KEY not found in environment or .env file. API calls will be skipped.")

# --- Chat Function with Streaming and Thought Simulation ---

def stream_openai_response(message: str, history: List[List[str]]) -> Iterator[List[Dict[str, Any]]]:
    """
    Connects to OpenAI, streams the response, and incorporates the agent 'thought' step.
    This function will be wrapped in a LangGraph Node in the next step.
    """
    
    # 1. Convert Gradio history into a list of ChatMessage objects (for yielding intermediate steps)
    chat_messages = []
    for user_content, assistant_content in history:
        if user_content:
            chat_messages.append(ChatMessage(role="user", content=user_content))
        if assistant_content:
            chat_messages.append(ChatMessage(role="assistant", content=assistant_content))

    # 2. Add the initial 'Thinking' message (Agent Simulation)
    thought_message = ChatMessage(
        content=f"Preparing LLM prompt for: '{message}'...",
        metadata={
            "title": "🧠 Agent Pre-Call Check",
            "log": f"Using {MODEL_NAME}...",
            "status": "pending" 
        }
    )
    chat_messages.append(thought_message)
    yield chat_messages # Show the thinking phase immediately

    # 3. Prepare message history for the OpenAI API call
    openai_messages = [{"role": "system", "content": "You are a concise, helpful technical assistant."}]
    
    # Map Gradio history (list of lists) to the API contents format
    for user_msg, assistant_msg in history:
        if user_msg:
            openai_messages.append({"role": "user", "content": user_msg})
        if assistant_msg:
            openai_messages.append({"role": "assistant", "content": assistant_msg})
    
    # Add the current user message
    openai_messages.append({"role": "user", "content": message})

    # 4. Stream the actual LLM response
    full_response_text = ""
    response_placeholder_index = -1 

    if client and OPENAI_API_KEY:
        try:
            # Initialize the final response message structure and append it to chat_messages
            final_response_message = ChatMessage(role="assistant", content="")
            chat_messages.append(final_response_message)
            response_placeholder_index = len(chat_messages) - 1
            
            # Start generation stream
            stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=openai_messages,
                stream=True,
            )
            
            # Stream the chunks
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content is not None:
                    full_response_text += content
                    
                    # Update the final response message content
                    chat_messages[response_placeholder_index].content = full_response_text
                    
                    # Update the thought message status to "done" (This closes the 'thinking' block)
                    thought_index = -2 # The thought is always the second to last item before the final response starts
                    chat_messages[thought_index].metadata["status"] = "done" 
                    
                    yield chat_messages
                    
        except Exception as e:
            full_response_text = f"An OpenAI API error occurred: {type(e).__name__}: {str(e)}"
            
            # Append the error message as the final response
            if response_placeholder_index != -1:
                chat_messages[response_placeholder_index].content = full_response_text
            else:
                chat_messages.append(ChatMessage(role="assistant", content=full_response_text))
            
            # Ensure the thought block is closed and indicates failure
            thought_index = -2 if response_placeholder_index != -1 else -1
            chat_messages[thought_index].metadata["status"] = "done"
            chat_messages[thought_index].metadata["title"] = "❌ API Error"

            yield chat_messages
            
    else:
        # Fallback if API key is not set up
        # This branch ensures the user knows they need to set the key
        import time 
        time.sleep(1)
        full_response_text = "ERROR: OpenAI API key not found. Please ensure you have a correctly formatted '.env' file in the same directory, or have set the OPENAI_API_KEY environment variable."
        
        # Ensure the thought block is closed and indicates failure
        thought_index = -1
        chat_messages[thought_index].content = "API initialization skipped: Key is missing."
        chat_messages[thought_index].metadata["title"] = "❌ API Key Missing"
        chat_messages[thought_index].metadata["status"] = "done" 
        
        # Append the error message as the final response
        final_response_message = ChatMessage(role="assistant", content=full_response_text)
        chat_messages.append(final_response_message)
        yield chat_messages

# --- Gradio Interface ---

demo = gr.ChatInterface(
    fn=stream_openai_response,
    title="Gradio Chatbot with Streaming OpenAI & Agent Thought Simulation",
    description=f"This MVP connects to the OpenAI API ({MODEL_NAME}) and streams the response while showing a simulated agent 'thought' step. **Your OPENAI_API_KEY is loaded securely via python-dotenv.**",
    examples=["What is LangGraph and why is it useful?", "Write a 3-point summary of the Agile manifesto."],
).launch()