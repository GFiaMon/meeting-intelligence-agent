# app_experiment_2.py
# Standard library imports
import os

# Third-party library imports
import gradio as gr
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

# Local/custom imports
from config import Config
from core.pinecone_manager import PineconeManager
from core.tools import search_meetings, get_meeting_metadata, list_recent_meetings, initialize_tools

# ============================================================
# CONFIGURATION: Standard LangChain Agent (Experimental 2)
# ============================================================
print("🧪 Using Standard LangChain Agent (create_tool_calling_agent)")

# 1. Initialize Services
try:
    pinecone_mgr = PineconeManager()
    # Initialize the tools with the manager (required for them to work)
    initialize_tools(pinecone_mgr)
    pinecone_available = True
except Exception as e:
    print(f"Warning: Pinecone not available: {e}")
    pinecone_mgr = None
    pinecone_available = False

# 2. Define Tools
# We use the same tools as the other agent
tools = [search_meetings, get_meeting_metadata, list_recent_meetings]

# 3. Initialize LLM
llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    temperature=0.7,
    openai_api_key=Config.OPENAI_API_KEY
)

# 4. Create the Agent
# We need a prompt template for the agent
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful meeting assistant. You can search for meetings, get metadata, and list recent meetings."),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# Create the tool calling agent (standard LangChain way)
agent = create_tool_calling_agent(llm, tools, prompt)

# 5. Create the Agent Executor
# This is the runtime that actually executes the agent's actions
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

def chat_with_agent(message, history):
    """
    Chat function that uses the standard LangChain AgentExecutor.
    """
    if not pinecone_available:
        return "❌ Pinecone service is not available."
    
    # Convert Gradio history to LangChain format if needed, 
    # but AgentExecutor handles chat_history in the prompt if we pass it.
    # For simplicity here, we'll just pass the current input.
    # A more complex implementation would format 'history' into {chat_history}
    
    try:
        # Invoke the agent
        response = agent_executor.invoke({"input": message})
        return response["output"]
    except Exception as e:
        return f"Error: {str(e)}"

# ============================================================
# Gradio Interface
# ============================================================
with gr.Blocks() as demo:
    gr.Markdown("# 🧪 Experiment 2: Standard LangChain Agent")
    gr.Markdown("This agent uses `create_tool_calling_agent` and `AgentExecutor` instead of LangGraph.")
    
    chatbot = gr.ChatInterface(
        fn=chat_with_agent,
        title="Standard LangChain Agent",
        examples=[
            "What meetings do I have?",
            "Summarize the last meeting",
        ]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7862)
