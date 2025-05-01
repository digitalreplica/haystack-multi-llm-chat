# pages/09_Debug.py

import streamlit as st
import json
from typing import Any, Dict

# Set page configuration
st.set_page_config(
    page_title="Debug - Haystack Multi-LLM Chat",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper function to make session state JSON serializable
def make_serializable(obj: Any) -> Any:
    """Convert non-serializable objects to strings for JSON serialization."""
    if hasattr(obj, "__dict__"):
        return str(obj)
    elif hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        return obj.to_dict()
    elif isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    else:
        try:
            # Try to serialize directly first
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            # If that fails, convert to string
            return str(obj)

# Main debug interface
st.title("🔍 Session State Debug")

# Convert session state to serializable format
serializable_state: Dict[str, Any] = {}
for key, value in st.session_state.items():
    serializable_state[key] = make_serializable(value)

# Format the JSON with indentation for readability
formatted_json = json.dumps(serializable_state, indent=2, sort_keys=True)

# Display the session state as JSON
st.code(formatted_json, language="json")

# Add a refresh button
if st.button("Refresh Session State", type="primary"):
    st.rerun()

# Empty sidebar to match other pages
with st.sidebar:
    st.title("Debug Tools")

    # Add a button to return to chat
    if st.button("← Back to Chat", use_container_width=True):
        st.switch_page("pages/03_Chat.py")

    # Add option to clear specific session state items
    with st.expander("Clear Session Items"):
        keys_to_clear = st.multiselect(
            "Select items to clear",
            options=list(st.session_state.keys())
        )

        if st.button("Clear Selected Items") and keys_to_clear:
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.success(f"Cleared {len(keys_to_clear)} item(s) from session state")
            st.rerun()