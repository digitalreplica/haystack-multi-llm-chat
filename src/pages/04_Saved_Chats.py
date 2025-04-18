# pages/03_Saved_Chats.py

import streamlit as st
import os
import json
from datetime import datetime
import pathlib
from haystack.dataclasses import ChatMessage

# Set page configuration
st.set_page_config(
    page_title="Saved Chats - Haystack Multi-LLM Chat",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Get the ConfigManager
config = st.session_state.config_manager

# Path for saved chats - now from ConfigManager
SAVE_DIR = pathlib.Path(config.get_global("base_directories", {}).get("saved_chats", "saved_chats"))
SAVE_DIR.mkdir(exist_ok=True)

# Helper functions
def format_timestamp(timestamp_str):
    """Convert filename timestamp to readable format"""
    try:
        date_obj = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
        return date_obj.strftime("%b %d, %Y at %I:%M %p")
    except:
        return timestamp_str

def get_saved_files():
    """Get list of saved chat files, sorted by modification time (newest first)"""
    if SAVE_DIR.exists():
        saved_files = list(SAVE_DIR.glob("chat_*.json"))
        saved_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return saved_files
    return []

def load_chat_file(file_path):
    """Load and validate a chat file"""
    try:
        with open(file_path, "r") as f:
            chat_data = json.load(f)

        # Validate basic structure
        if not isinstance(chat_data, dict) or "messages" not in chat_data or "metadata" not in chat_data:
            return None, "Invalid chat file format"

        return chat_data, None
    except Exception as e:
        return None, f"Error loading chat: {str(e)}"

def save_current_chat():
    """Save the current chat session to a JSON file"""
    # Create a unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chat_{timestamp}.json"
    file_path = SAVE_DIR / filename

    # Prepare the chat data structure
    chat_data = {
        "messages": [msg.to_dict() for msg in st.session_state.messages],
        "metadata": {
            "timestamp": timestamp,
            "saved_at": datetime.now().isoformat(),
            # Add document information
            "documents": {
                "selected_documents": st.session_state.get("selected_documents", []),
                "document_format": config.get_page_config("documents", "format", "xml"),
                "document_instructions": config.get_page_config("documents", "instructions", "")
            }
        }
    }

    # Save to file
    try:
        with open(file_path, "w") as f:
            json.dump(chat_data, f, indent=2)
        return f"Chat saved successfully as {filename}"
    except Exception as e:
        return f"Error saving chat: {str(e)}"

def load_chat_to_session(chat_data):
    """Load a saved chat into the current session"""
    try:
        # Convert the dictionary messages back to ChatMessage objects
        messages = []
        for msg_dict in chat_data["messages"]:
            messages.append(ChatMessage.from_dict(msg_dict))

        # Update session state
        st.session_state.messages = messages

        # Restore document information if available
        if "documents" in chat_data["metadata"]:
            doc_data = chat_data["metadata"]["documents"]

            if "selected_documents" in doc_data:
                st.session_state.selected_documents = doc_data["selected_documents"]

            # Note: We're not updating the configuration with document format and instructions
            # as these are now managed by ConfigManager

        return True, "Chat loaded successfully!"
    except Exception as e:
        return False, f"Error loading chat into session: {str(e)}"

# Main page content
st.title("📚 Saved Chats")
st.write("Manage your saved conversations and load them into the chat interface.")

# Sidebar for chat selection and management
with st.sidebar:
    st.title("Saved Chats")

    # Save current chat button
    if st.button("Save Current Chat", type="primary", use_container_width=True):
        result = save_current_chat()
        st.success(result)
        # Refresh the file list
        st.rerun()

    st.divider()

    # Get list of saved chat files
    saved_files = get_saved_files()

    if not saved_files:
        st.info("No saved chats found")
    else:
        st.write(f"**{len(saved_files)} saved chat(s)**")

        # Create a dictionary of display names to file paths
        display_names = {}
        for file in saved_files:
            # Extract timestamp from filename
            timestamp_str = file.stem.replace("chat_", "")
            display_name = format_timestamp(timestamp_str)
            display_names[display_name] = file

        # Create a radio button for chat selection
        selected_display = st.radio(
            "Select a chat to preview:",
            options=list(display_names.keys())
        )

        # Store the selected file path in session state
        if selected_display:
            st.session_state.selected_chat_file = display_names[selected_display]

            # Add option to delete the selected chat
            if st.button("Delete Selected Chat", type="secondary", use_container_width=True):
                try:
                    os.remove(st.session_state.selected_chat_file)
                    st.success(f"Deleted: {st.session_state.selected_chat_file.name}")
                    # Clear the selection
                    if "selected_chat_file" in st.session_state:
                        del st.session_state.selected_chat_file
                    if "preview_chat_data" in st.session_state:
                        del st.session_state.preview_chat_data
                    # Refresh the page
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting file: {str(e)}")

    # Navigation buttons
    st.divider()
    if st.button("← Back to Chat", use_container_width=True):
        st.switch_page("pages/03_Chat.py")

    if st.button("← Back to Model Selection", use_container_width=True):
        st.switch_page("pages/01_Model_Selection.py")

# Main panel - Chat preview and loading
if "selected_chat_file" in st.session_state:
    selected_file = st.session_state.selected_chat_file

    # Load the chat data for preview
    chat_data, error = load_chat_file(selected_file)

    if error:
        st.error(error)
    else:
        st.session_state.preview_chat_data = chat_data

        # Display chat metadata
        st.subheader("Chat Information")
        metadata = chat_data["metadata"]

        # Format the timestamp if available
        timestamp = metadata.get("timestamp", "")
        if timestamp:
            timestamp_display = format_timestamp(timestamp)
        else:
            timestamp_display = metadata.get("saved_at", "Unknown date")

        # Display saved date
        st.write(f"**Date:** {timestamp_display}")

        # Display model information if available in older saved chats
        if "selected_models" in metadata:
            st.write(f"**Models:** {', '.join([m['name'] for m in metadata['selected_models']])}")
            st.info("Note: Model configuration is now managed separately and won't be restored when loading this chat.")

        # Display document information if available
        if "documents" in metadata and metadata["documents"].get("selected_documents"):
            doc_data = metadata["documents"]
            doc_count = len(doc_data.get("selected_documents", []))
            st.write(f"**Documents:** {doc_count} file(s) included")

            # Show document format and names in an expander
            with st.expander("View Document Details"):
                st.write(f"**Format:** {doc_data.get('document_format', 'xml')}")
                st.write("**Files:**")
                for doc in doc_data.get("selected_documents", []):
                    st.write(f"- {doc.get('path', 'Unknown file')}")

        # Chat preview
        st.subheader("Chat Preview")

        # Display the messages in the chat preview
        preview_container = st.container(height=400, border=True)
        with preview_container:
            for msg_dict in chat_data["messages"]:
                role = msg_dict.get("role", "unknown")
                content = msg_dict.get("content", "")

                if role == "user":
                    st.markdown(f"**User:** {content}")
                elif role == "assistant":
                    meta = msg_dict.get("meta", {})
                    model_name = meta.get("model_name", "Assistant")
                    provider = meta.get("provider", "")
                    selected = meta.get("selected", False)

                    # Add a visual indicator for selected responses
                    prefix = "✓ " if selected else ""

                    st.markdown(f"**{prefix}{model_name} ({provider}):** {content}")
                st.divider()

        # Load button
        if st.button("Load This Chat Into Active Session", type="primary"):
            success, message = load_chat_to_session(chat_data)
            if success:
                st.success(message)
                st.info("Switching to chat interface...")
                # Add a small delay for the user to see the success message
                import time
                time.sleep(1)
                st.switch_page("pages/03_Chat.py")
            else:
                st.error(message)
else:
    # No chat selected
    st.info("👈 Select a saved chat from the sidebar to preview it here.")
    st.write("You can also save your current chat session using the 'Save Current Chat' button in the sidebar.")