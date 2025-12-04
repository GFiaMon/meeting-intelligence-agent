# PEP 8 Import Standards

## Overview

This project follows **PEP 8** (Python Enhancement Proposal 8) - the official Python style guide for organizing imports.

## Import Organization Rules

Imports should be organized in **3 groups**, separated by blank lines:

### 1. Standard Library Imports
Built-in Python modules (come with Python installation)

```python
# Standard library imports
import os
import random
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
```

### 2. Third-Party Imports
External packages installed via pip

```python
# Third-party imports
import gradio as gr
import numpy as np
from langchain_core.messages import AIMessage, HumanMessage
from langsmith import Client, RunTree
from openai import OpenAI
```

### 3. Local Application Imports
Your own project modules

```python
# Local application imports
from src.config.settings import Config
from src.tools.video import get_video_state
from src.agents.conversational import ConversationalAgent
```

## Additional Rules

### Alphabetical Sorting
Within each group, imports should be sorted alphabetically:

✅ **Good:**
```python
# Third-party imports
import gradio as gr
from langchain_core.messages import AIMessage, HumanMessage
from langsmith import Client
```

❌ **Bad:**
```python
# Third-party imports
from langsmith import Client
import gradio as gr
from langchain_core.messages import AIMessage, HumanMessage
```

### Multi-line Imports
For long import lists, use parentheses and one import per line:

✅ **Good:**
```python
from src.tools.video import (
    cancel_video_workflow,
    initialize_video_tools,
    request_transcription_edit,
    request_video_upload,
    transcribe_uploaded_video,
    update_speaker_names,
    update_transcription,
    upload_transcription_to_pinecone,
)
```

❌ **Bad:**
```python
from src.tools.video import cancel_video_workflow, initialize_video_tools, request_transcription_edit, request_video_upload, transcribe_uploaded_video, update_speaker_names, update_transcription, upload_transcription_to_pinecone
```

### Avoid Inline Imports
Don't import inside functions unless absolutely necessary (e.g., avoiding circular imports):

✅ **Good:**
```python
# At top of file
from langsmith import RunTree

def my_function():
    run_tree = RunTree(...)
```

❌ **Bad:**
```python
def my_function():
    from langsmith import RunTree  # Avoid this
    run_tree = RunTree(...)
```

## Complete Example

```python
"""
Module docstring explaining what this file does.
"""

# Standard library imports
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Third-party imports
import gradio as gr
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langsmith import Client, RunTree

# Local application imports
from src.config.settings import Config
from src.tools.general import (
    get_meeting_metadata,
    initialize_tools,
    search_meetings,
)
from src.tools.video import get_video_state


def my_function():
    """Function implementation."""
    pass
```

## Benefits

1. **Readability**: Easy to see what dependencies a module has
2. **Maintainability**: Easier to spot missing or unused imports
3. **Consistency**: All files follow the same pattern
4. **Debugging**: Quickly identify import errors by section

## Tools

### Automatic Formatting
Use these tools to automatically format imports:

- **isort**: Automatically sorts imports
  ```bash
  pip install isort
  isort your_file.py
  ```

- **black**: Code formatter (also handles imports)
  ```bash
  pip install black
  black your_file.py
  ```

### VS Code Settings
Add to `.vscode/settings.json`:
```json
{
    "python.sortImports.args": [
        "--profile", "black"
    ],
    "[python]": {
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

## References

- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 8 - Imports Section](https://peps.python.org/pep-0008/#imports)
- [isort Documentation](https://pycqa.github.io/isort/)

## Project Status

✅ Files following PEP 8 import standards:
- `src/agents/conversational.py`
- `src/ui/gradio_app.py`

All new files should follow this standard from the start.
