"""
World Time MCP Server - Upgraded version with city parameter
=============================================================

This is an upgraded MCP server that allows the LLM to specify
which city's time to retrieve.

This demonstrates how to create MCP tools with parameters.
"""

from datetime import datetime
import pytz
import gradio as gr


def get_time_for_city(city: str = "Berlin"):
    """
    Get current time for any major city.
    
    Args:
        city: City name (e.g., "Berlin", "Tokyo", "New York", "London")
    
    Returns:
        dict: Time information for the specified city, or error if city not found
    """
    # Map common city names to IANA timezones
    city_timezones = {
        "berlin": "Europe/Berlin",
        "london": "Europe/London",
        "paris": "Europe/Paris",
        "madrid": "Europe/Madrid",
        "rome": "Europe/Rome",
        "new york": "America/New_York",
        "los angeles": "America/Los_Angeles",
        "chicago": "America/Chicago",
        "toronto": "America/Toronto",
        "mexico city": "America/Mexico_City",
        "tokyo": "Asia/Tokyo",
        "beijing": "Asia/Shanghai",
        "hong kong": "Asia/Hong_Kong",
        "singapore": "Asia/Singapore",
        "dubai": "Asia/Dubai",
        "sydney": "Australia/Sydney",
        "melbourne": "Australia/Melbourne",
        "auckland": "Pacific/Auckland",
        "moscow": "Europe/Moscow",
        "istanbul": "Europe/Istanbul",
        "cairo": "Africa/Cairo",
        "johannesburg": "Africa/Johannesburg",
        "sao paulo": "America/Sao_Paulo",
        "buenos aires": "America/Argentina/Buenos_Aires",
    }
    
    # Normalize city name
    city_lower = city.lower().strip()
    
    # Check if city is known
    if city_lower not in city_timezones:
        return {
            "error": f"Unknown city: {city}",
            "message": "Please use one of the available cities",
            "available_cities": sorted(city_timezones.keys())
        }
    
    # Get timezone and current time
    timezone_name = city_timezones[city_lower]
    tz = pytz.timezone(timezone_name)
    current_time = datetime.now(tz)
    
    return {
        "city": city.title(),
        "time": current_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "timezone": timezone_name,
        "timestamp": current_time.isoformat(),
        "utc_offset": current_time.strftime("%z"),
        "day_of_week": current_time.strftime("%A"),
        "is_dst": bool(current_time.dst())
    }


# Interface with input parameter
demo = gr.Interface(
    fn=get_time_for_city,
    inputs=gr.Textbox(
        label="City Name",
        placeholder="Enter city (e.g., Berlin, Tokyo, New York)",
        value="Berlin"
    ),
    outputs=gr.JSON(label="Time Information"),
    title="🌍 World Time MCP Server",
    description="""
    This is an MCP server that provides the current time for any major city.
    
    **For Testing:** Enter a city name and click 'Submit'.
    
    **For AI Agents:** This server exposes the `get_time_for_city` tool via MCP protocol.
    The LLM can specify which city's time to retrieve.
    
    **Example cities:** Berlin, Tokyo, New York, London, Paris, Sydney
    """,
    examples=[
        ["Berlin"],
        ["Tokyo"],
        ["New York"],
        ["London"],
        ["Sydney"]
    ],
    api_name="get_time_for_city"
)

if __name__ == "__main__":
    # Launch with MCP server enabled
    demo.launch(
        mcp_server=True,
        share=False,
        server_name="0.0.0.0",
        server_port=7860  # Different port so both can run simultaneously
    )
