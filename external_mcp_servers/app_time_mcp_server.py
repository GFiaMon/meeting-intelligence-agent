"""
Berlin Time MCP Server - A Gradio-based MCP server example
===========================================================

This is a simple MCP (Model Context Protocol) server that provides
a tool for getting the current time in Berlin timezone.

MCP servers allow AI agents to discover and use tools in a standardized way.
"""

from datetime import datetime
import pytz
import gradio as gr


def get_berlin_time():
    """
    Get the current date and time in Berlin timezone.
    
    This function will be exposed as an MCP tool that AI agents can call
    when they need to know the current time in Berlin.
    
    Returns:
        dict: A dictionary containing:
            - time: Human-readable formatted time string
            - timezone: The timezone name (Europe/Berlin)
            - timestamp: ISO 8601 formatted timestamp
            - utc_offset: Current UTC offset for Berlin
    """
    # Create Berlin timezone object
    berlin_tz = pytz.timezone('Europe/Berlin')
    
    # Get current time in Berlin
    current_time = datetime.now(berlin_tz)
    
    # Format the time in a human-readable way
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    
    # Get UTC offset (e.g., +01:00 or +02:00 depending on DST)
    utc_offset = current_time.strftime("%z")
    
    # Return structured data
    return {
        "time": formatted_time,
        "timezone": "Europe/Berlin",
        "timestamp": current_time.isoformat(),
        "utc_offset": utc_offset,
        "day_of_week": current_time.strftime("%A"),
        "is_dst": bool(current_time.dst())
    }


# Simple Interface - just like the example you showed
demo = gr.Interface(
    fn=get_berlin_time,
    inputs=[],  # Empty list = no inputs needed
    outputs=gr.JSON(label="Berlin Time Information"),
    title="🕐 Berlin Time MCP Server",
    description="""
    This is an MCP (Model Context Protocol) server that provides the current time in Berlin.
    
    **For Testing:** Click 'Submit' below to see the current Berlin time.
    
    **For AI Agents:** This server exposes the `get_berlin_time` tool via MCP protocol.
    AI agents can connect to this server and call this tool when they need Berlin time.
    """,
    api_name="get_berlin_time"
)

if __name__ == "__main__":
    # Launch with MCP server enabled
    # We use quiet=True to prevent Gradio from printing to stdout,
    # which would interfere with the MCP stdio protocol.
    demo.launch(
        mcp_server=True,
        share=False,
        server_name="0.0.0.0",
        server_port=7860,
        quiet=True
    )
