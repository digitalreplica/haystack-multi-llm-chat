# pages/02_Documents.py

import streamlit as st
import os
import pathlib
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Documents - Haystack Multi-LLM Chat",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Get the ConfigManager instance
config = st.session_state.config_manager

# Initialize session state for documents if it doesn't exist
if "selected_documents" not in st.session_state:
    st.session_state.selected_documents = []  # List of {path, content, timestamp}

# Function to list files in a directory
def list_files(directory, recursive=False, show_ignored=False):
    try:
        directory_path = pathlib.Path(directory)
        if not directory_path.exists() or not directory_path.is_dir():
            return [], f"Error: '{directory}' is not a valid directory"

        # Get ignore list from config
        ignore_dirs = set() if show_ignored else set(config.get_global("ignored_directories", []))

        files = []

        if recursive:
            # Use manual traversal for recursive search with ignore logic
            for path in directory_path.rglob('*'):
                # Check if any parent directory is in the ignore list
                should_ignore = any(ignore_dir in path.parts for ignore_dir in ignore_dirs)
                if path.is_file() and not should_ignore:
                    files.append(str(path.relative_to(directory_path)))
        else:
            # Use glob for non-recursive search
            files = [str(p.relative_to(directory_path)) for p in directory_path.glob("*") 
                    if p.is_file() and p.name not in ignore_dirs]

        # Sort alphabetically
        files.sort()
        return files, None
    except Exception as e:
        return [], f"Error listing files: {str(e)}"

# Function to read file content
def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read(), None
    except UnicodeDecodeError:
        try:
            # Try with a different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read(), None
        except Exception as e:
            return "", f"Error reading file (encoding issue): {str(e)}"
    except Exception as e:
        return "", f"Error reading file: {str(e)}"

# Function to format document content based on selected format
def format_document(name, content, format_type):
    if format_type == "xml":
        return f'<document name="{name}">\n{content}\n</document>'
    elif format_type == "markdown":
        # Try to determine language for syntax highlighting
        extension = pathlib.Path(name).suffix.lower()
        # Get language mappings from config
        lang_map = config.get_page_config(
            "documents", 
            "language_mappings", 
            {
                '.py': 'python',
                '.js': 'javascript',
                '.html': 'html',
                '.css': 'css',
                '.java': 'java',
                '.cpp': 'cpp', '.c': 'c',
                '.json': 'json',
                '.md': 'markdown',
                '.sh': 'bash',
                '.sql': 'sql',
                '.txt': ''
            }
        )
        lang = lang_map.get(extension, '')

        return f'```{lang} {name}\n{content}\n```'
    elif format_type == "simple":
        return f'--- {name} ---\n{content}\n'
    else:
        return f'# {name}\n{content}\n'

# Function to generate preview of formatted documents
def generate_preview():
    if not st.session_state.selected_documents:
        return "No documents selected."

    # Get format with fallback to global documents section
    format_type = config.get_page_config_with_fallback("documents", "format", "documents", "format", "xml")

    # Get instructions with fallback to global documents section
    instructions = config.get_page_config_with_fallback(
        "documents", 
        "instructions", 
        "documents",
        "instructions",
        ""
    )

    preview = instructions + "\n\n"

    for doc in st.session_state.selected_documents:
        preview += format_document(doc["path"], doc["content"], format_type) + "\n\n"

    return preview

# Function to add a document to the selected list
def add_document(file_path, base_dir):
    # Check if document is already selected
    for doc in st.session_state.selected_documents:
        if doc["path"] == file_path:
            return  # Already selected

    # Read file content
    full_path = os.path.join(base_dir, file_path)
    content, error = read_file_content(full_path)

    if error:
        st.error(error)
        return

    # Add to selected documents with timestamp for ordering
    st.session_state.selected_documents.append({
        "path": file_path,
        "content": content,
        "timestamp": datetime.now().timestamp()
    })

# Function to remove a document from the selected list
def remove_document(file_path):
    st.session_state.selected_documents = [
        doc for doc in st.session_state.selected_documents 
        if doc["path"] != file_path
    ]

# Main content
st.title("📄 Document Selection")
st.markdown("Select documents to include in your chat session.")

# Directory selection
col1, col2 = st.columns([3, 1])

with col1:
    # Get the base directory from config
    default_base_folder = config.get_global("base_directories", {}).get("documents", os.getcwd())

    # Get the current base folder from page config or use the default
    current_base_folder = config.get_page_config("documents", "base_folder", default_base_folder)

    base_folder = st.text_input(
        "Base Folder Path", 
        value=current_base_folder,
        help="Enter the folder path to browse for documents"
    )

    # Update config if changed
    if base_folder != current_base_folder:
        config.set_page_config("documents", "base_folder", base_folder)

with col2:
    # Get recursive setting from config
    recursive = st.checkbox("Search Recursively", 
                           value=config.get_page_config("documents", "recursive", False))

    # Update config if changed
    if recursive != config.get_page_config("documents", "recursive", False):
        config.set_page_config("documents", "recursive", recursive)

    # Get show_ignored setting from config
    show_ignored = st.checkbox("Show Ignored Directories", 
                              value=config.get_page_config("documents", "show_ignored_dirs", False),
                              help="Show files in directories that are normally ignored")

    # Update config if changed
    if show_ignored != config.get_page_config("documents", "show_ignored_dirs", False):
        config.set_page_config("documents", "show_ignored_dirs", show_ignored)

# Refresh button
if st.button("Refresh File List", type="primary"):
    # Force refresh - no need to update anything as we're already using config values
    pass

# List files in the directory
files, error = list_files(base_folder, recursive, show_ignored)

if error:
    st.error(error)
elif not files:
    st.info(f"No files found in '{base_folder}'")
else:
    # Create two columns: one for file selection, one for selected files
    col_files, col_selected = st.columns(2)

    with col_files:
        st.subheader("Available Files")

        # Group files by directory if recursive
        if recursive:
            # Group files by directory
            files_by_dir = {}
            for file in files:
                dir_name = os.path.dirname(file) or "."
                if dir_name not in files_by_dir:
                    files_by_dir[dir_name] = []
                files_by_dir[dir_name].append(file)

            # Display files grouped by directory with expanders
            for dir_name, dir_files in sorted(files_by_dir.items()):
                with st.expander(f"📁 {dir_name}"):
                    for file in sorted(dir_files):
                        # Check if file is already selected
                        is_selected = any(doc["path"] == file for doc in st.session_state.selected_documents)

                        col_check, col_name = st.columns([1, 4])
                        with col_check:
                            if st.checkbox("", value=is_selected, key=f"file_{file}", 
                                          on_change=add_document if not is_selected else remove_document,
                                          args=([file, base_folder] if not is_selected else [file])):
                                pass  # Checkbox state is handled by on_change
                        with col_name:
                            st.write(os.path.basename(file))
        else:
            # Display files directly
            for file in files:
                # Check if file is already selected
                is_selected = any(doc["path"] == file for doc in st.session_state.selected_documents)

                col_check, col_name = st.columns([1, 4])
                with col_check:
                    if st.checkbox("", value=is_selected, key=f"file_{file}", 
                                  on_change=add_document if not is_selected else remove_document,
                                  args=([file, base_folder] if not is_selected else [file])):
                        pass  # Checkbox state is handled by on_change
                with col_name:
                    st.write(file)

    with col_selected:
        st.subheader("Selected Documents")

        if not st.session_state.selected_documents:
            st.info("No documents selected. Check files on the left to include them.")
        else:
            # Sort selected documents by selection time
            selected_docs = sorted(st.session_state.selected_documents, key=lambda x: x["timestamp"])

            # Display selected documents with remove button
            for i, doc in enumerate(selected_docs):
                with st.container(border=True):
                    col_name, col_remove = st.columns([4, 1])
                    with col_name:
                        st.write(f"{i+1}. {doc['path']}")
                        st.caption(f"{len(doc['content'])} characters")
                    with col_remove:
                        if st.button("🗑️", key=f"remove_{i}", on_click=remove_document, args=(doc["path"],)):
                            pass  # Button action handled by on_click

            # Clear all button
            if st.button("Clear All", type="secondary"):
                st.session_state.selected_documents = []
                st.rerun()

# Document formatting options
st.markdown("---")
st.subheader("Document Formatting")

# Get format options from config with fallback to global documents section
format_options = config.get_page_config_with_fallback(
    "documents", 
    "format_options",
    "documents",
    "format_options", 
    {
        "xml": "XML Tags (<document name=\"filename\">content</document>)",
        "markdown": "Markdown (```filename\ncontent```)",
        "simple": "Simple Text (--- filename ---\ncontent)"
    }
)

# Get current format from config with fallback to global documents section
current_format = config.get_page_config_with_fallback("documents", "format", "documents", "format", "xml")

selected_format = st.radio(
    "Select document format style:",
    options=list(format_options.keys()),
    format_func=lambda x: format_options[x],
    index=list(format_options.keys()).index(current_format) if current_format in format_options else 0,
    horizontal=True
)

# Update format in page-specific config if changed
if selected_format != current_format:
    config.set_page_config("documents", "format", selected_format)

# Document instructions
st.subheader("Document Instructions")
st.caption("This text will be prepended to the documents when sending to the model")

# Get current instructions from config with fallback to global documents section
current_instructions = config.get_page_config_with_fallback(
    "documents", 
    "instructions",
    "documents",
    "instructions", 
    "I'm sharing some documents with you below. Please help me understand, analyze, "
    "or modify these documents based on my questions. Reference the document names "
    "when discussing specific parts."
)

document_instructions = st.text_area(
    "Instructions for the AI",
    value=current_instructions,
    height=100
)

# Update instructions in page-specific config if changed
if document_instructions != current_instructions:
    config.set_page_config("documents", "instructions", document_instructions)

# Preview section
st.markdown("---")
st.subheader("Preview")
st.caption("This is how your documents will be formatted and sent to the model")

with st.expander("Show Preview", expanded=True):
    preview_text = generate_preview()
    st.code(preview_text, language="text")

# Navigation buttons
st.markdown("---")
col_back, col_spacer, col_next = st.columns([1, 2, 1])

with col_back:
    if st.button("← Back to Model Selection", type="secondary", use_container_width=True):
        st.switch_page("pages/01_Model_Selection.py")

with col_next:
    # Only enable the Start Chat button if we have selected models
    start_disabled = "selected_models" not in st.session_state or len(st.session_state.selected_models) == 0

    if st.button("Start Chat →", type="primary", disabled=start_disabled, use_container_width=True):
        if not start_disabled:
            # Initialize/reset chat history
            st.session_state.messages = []
            st.session_state.last_user_msg_idx = -1
            if "awaiting_selection" in st.session_state:
                del st.session_state.awaiting_selection

            # Navigate to chat page
            st.switch_page("pages/03_Chat.py")
        else:
            st.error("Please configure models before starting chat.")

# Sidebar with information
with st.sidebar:
    st.title("Document Co-Editing")
    st.write("""
    This feature allows you to include documents in your chat session for reference or editing.

    **How it works:**
    1. Select documents from the file browser
    2. Choose a formatting style
    3. Customize the instructions for the AI
    4. Start the chat session

    The selected documents will be included in the first message to the AI.
    """)

    st.info("💡 **Tip:** For best results with large documents, be specific in your instructions about which parts of the document you want the AI to focus on.")

    # Show document stats
    st.subheader("Document Statistics")
    total_docs = len(st.session_state.selected_documents)
    total_chars = sum(len(doc["content"]) for doc in st.session_state.selected_documents)

    st.metric("Selected Documents", total_docs)
    st.metric("Total Characters", total_chars)

    # Get character to token ratio from config
    char_to_token_ratio = config.get_page_config("documents", "char_to_token_ratio", 4)
    est_tokens = total_chars // char_to_token_ratio
    st.metric("Estimated Tokens", est_tokens)

    # Get token warning threshold from config
    token_warning_threshold = config.get_page_config("documents", "token_warning_threshold", 8000)
    if est_tokens > token_warning_threshold:
        st.warning(f"⚠️ Selected documents may exceed context limits of some models ({est_tokens} tokens).")

    # Advanced settings expander for ignored directories
    with st.expander("Advanced Settings"):
        st.subheader("Ignored Directories")
        st.caption("These directories are skipped when browsing files")

        # Get ignored directories from config
        ignored_dirs_list = sorted(config.get_global("ignored_directories", []))
        ignored_dirs_text = st.text_area(
            "One directory name per line:", 
            value="\n".join(ignored_dirs_list),
            height=150
        )

        # Update the ignored directories if changed
        if st.button("Update Ignored Directories"):
            # Split by newlines and filter out empty lines
            new_ignored_dirs = [dir.strip() for dir in ignored_dirs_text.split("\n") if dir.strip()]
            config.set_global("ignored_directories", new_ignored_dirs)
            st.success("Ignored directories updated!")

        # Character to token ratio setting
        char_to_token_ratio = config.get_page_config("documents", "char_to_token_ratio", 4)
        new_char_to_token_ratio = st.number_input(
            "Characters per token:", 
            min_value=1, 
            max_value=10, 
            value=char_to_token_ratio,
            help="Used for estimating token count from character count"
        )

        if new_char_to_token_ratio != char_to_token_ratio:
            config.set_page_config("documents", "char_to_token_ratio", int(new_char_to_token_ratio))

        # Token warning threshold setting
        token_warning_threshold = config.get_page_config("documents", "token_warning_threshold", 8000)
        new_token_warning_threshold = st.number_input(
            "Token warning threshold:", 
            min_value=1000, 
            max_value=100000, 
            value=token_warning_threshold,
            step=1000,
            help="Show warning when estimated tokens exceed this value"
        )

        if new_token_warning_threshold != token_warning_threshold:
            config.set_page_config("documents", "token_warning_threshold", int(new_token_warning_threshold))
