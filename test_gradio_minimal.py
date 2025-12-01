"""
Minimal Gradio test to isolate UI issues
"""

import gradio as gr
from typing import Generator, List

def simple_chat(message: str, history: List[List[str]]) -> Generator[str, None, None]:
    """Simple test chat function"""
    yield f"Echo: {message}"

print("Testing minimal Gradio interface...")

with gr.Blocks() as demo:
    gr.Markdown("# Test Chat Interface")
    
    chatbot_ui = gr.Chatbot(label="Test Bot", height=400)
    
    msg_input = gr.Textbox(label="Message", placeholder="Type here...")
    submit_btn = gr.Button("Send")
    
    def user_msg(message, history):
        return "", history + [[message, None]]
    
    def bot_response(history):
        user_message = history[-1][0]
        history[-1][1] = ""
        for chunk in simple_chat(user_message, history[:-1]):
            history[-1][1] = chunk
            yield history
    
    submit_btn.click(
        user_msg,
        [msg_input, chatbot_ui],
        [msg_input, chatbot_ui],
        queue=False
    ).then(
        bot_response,
        chatbot_ui,
        chatbot_ui
    )

if __name__ == "__main__":
    print("Launching minimal test...")
    demo.launch(server_port=7863, share=False)
