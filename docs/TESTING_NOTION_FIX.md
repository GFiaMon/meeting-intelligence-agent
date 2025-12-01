# Testing the Notion Integration Fix

## ✅ The Fix is Applied!

Your agent now properly supports async Notion MCP tools. The app is running at:
**http://localhost:7862**

## What Was Fixed

The agent was loading Notion tools correctly, but failing to execute them because:
- Notion MCP tools require **async execution**
- The agent was using **sync execution** (`graph.stream()`)
- This caused silent failures with generic error messages

**The fix:** Changed to async execution (`graph.astream()`) in both:
1. `core/conversational_agent.py` - The agent's response generator
2. `app_experiment_3.py` - The Gradio chat interface

## How to Test

### Test 1: Simple Page Creation
Open the app and try:
```
Create a test page in Notion with the title "My Test Page"
```

**Expected behavior:**
- You'll see: `📝 Calling Notion: API-post-page...`
- The agent will create the page and give you a link

### Test 2: Search Notion
```
Search Notion for pages about meetings
```

**Expected behavior:**
- You'll see: `📝 Calling Notion: API-post-search...`
- The agent will return search results

### Test 3: Meeting Minutes Export
```
Create meeting minutes in Notion for the last meeting
```

**Expected behavior:**
- Agent will first search for the meeting
- Then create a formatted page in Notion with the minutes

## What You Should See

When the agent uses Notion tools, you'll now see progress indicators:
- `📝 Calling Notion: API-post-page...` - Creating a page
- `📝 Calling Notion: API-post-search...` - Searching
- `📝 Calling Notion: API-append-block-children...` - Adding content

## Troubleshooting

### If the agent still refuses to use Notion tools:

1. **Check environment variables:**
   ```bash
   # Make sure these are set in .env:
   ENABLE_MCP=true
   NOTION_TOKEN=your_integration_secret
   ```

2. **Verify Notion permissions:**
   - Go to your Notion page
   - Click "..." → "Add connections"
   - Select your integration

3. **Check the terminal output:**
   - Look for "✅ Integrated 19 MCP tools into agent"
   - If you see this, tools are loaded correctly

4. **Try being more explicit:**
   Instead of: "Create a page"
   Try: "Use the Notion API to create a new page with title 'Test'"

## Default Parent Page

The agent is configured to create pages under:
- **Page ID:** `2bc5a424-5cbb-80ec-8aa9-c4fd989e67bc`
- **Page Name:** "Meetings Summary Test"

You can change this in the system prompt (line 103 in `conversational_agent.py`).

## Debug Scripts

If you need to debug further:
- `python debug_notion_tools.py` - Comprehensive diagnostics
- `python test_notion_fix.py` - Verify the async fix works

## Success Indicators

✅ Tools loading: "✅ Integrated 19 MCP tools into agent"
✅ Tool execution: "📝 Calling Notion: API-post-page..."
✅ Page created: Link to the new Notion page

## Next Steps

Now that Notion integration works, you can:
1. Create meeting minutes automatically
2. Export summaries to Notion
3. Search your Notion workspace
4. Manage pages through the agent

Enjoy! 🎉
