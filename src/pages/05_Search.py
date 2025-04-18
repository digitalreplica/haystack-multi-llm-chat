# pages/05_Search.py

import streamlit as st
import os
import pathlib
from datetime import datetime
import re
from typing import List, Dict, Tuple, Any, Optional

# Updated imports for Haystack 2.x
from haystack import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever

# Set page configuration
st.set_page_config(
    page_title="Search Documents - Haystack Multi-LLM Chat",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Get the ConfigManager instance
config = st.session_state.config_manager

# Initialize session state for search if it doesn't exist
if "selected_search_results" not in st.session_state:
    st.session_state.selected_search_results = []  # List of {path, content, timestamp, is_snippet}

if "search_document_store" not in st.session_state:
    st.session_state.search_document_store = None

if "search_retriever" not in st.session_state:
    st.session_state.search_retriever = None

if "indexed_files" not in st.session_state:
    st.session_state.indexed_files = set()  # Track which files have been indexed

if "base_folder" not in st.session_state:
    # Get base directory from config instead of hardcoding
    base_dir = config.get_global("base_directories", {}).get("search", "./data/search")
    st.session_state.base_folder = base_dir

if "last_search_results" not in st.session_state:
    st.session_state.last_search_results = []

if "last_search_query" not in st.session_state:
    st.session_state.last_search_query = ""

# Function to split markdown text into paragraphs with size limits
def split_by_paragraphs(markdown_text: str, file_path: str, max_chunk_size: int = 4000) -> List[Document]:
    """
    Split markdown text into chunks based on paragraphs with a maximum size limit.
    Returns a list of Haystack Document objects.
    """
    paragraphs = re.split(r'\n\s*\n', markdown_text)
    chunks = []
    current_chunk = ""
    chunk_index = 0

    for para in paragraphs:
        para = para.strip()
        if not para:  # Skip empty paragraphs
            continue

        # If adding this paragraph would exceed the chunk size,
        # save the current chunk and start a new one
        if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
            chunks.append(
                Document(
                    content=current_chunk,
                    meta={
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "chunk_index": chunk_index,
                        "is_snippet": True
                    }
                )
            )
            chunk_index += 1
            current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(
            Document(
                content=current_chunk,
                meta={
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "chunk_index": chunk_index,
                    "is_snippet": True
                }
            )
        )

    return chunks

# Function to list markdown files in a directory
def list_markdown_files(directory: str, recursive: bool = False, show_ignored: bool = False) -> Tuple[List[str], Optional[str]]:
    """
    List all markdown files in the given directory.
    Returns a list of file paths and an error message if any.
    """
    try:
        directory_path = pathlib.Path(directory)
        if not directory_path.exists() or not directory_path.is_dir():
            return [], f"Error: '{directory}' is not a valid directory"

        # Get ignore list from config
        ignore_dirs = set() if show_ignored else set(config.get_global("ignored_directories", []))

        files = []

        if recursive:
            # Use manual traversal for recursive search with ignore logic
            for path in directory_path.rglob('*.md'):
                # Check if any parent directory is in the ignore list
                should_ignore = any(ignore_dir in path.parts for ignore_dir in ignore_dirs)
                if not should_ignore:
                    files.append(str(path.relative_to(directory_path)))
        else:
            # Use glob for non-recursive search
            files = [str(p.relative_to(directory_path)) for p in directory_path.glob("*.md") 
                    if p.is_file() and p.name not in ignore_dirs]

        # Sort alphabetically
        files.sort()
        return files, None
    except Exception as e:
        return [], f"Error listing files: {str(e)}"

# Function to read file content
def read_file_content(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Read content from a file.
    Returns the content and an error message if any.
    """
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

# Function to initialize the document store and retriever
def initialize_search_engine() -> Tuple[InMemoryDocumentStore, InMemoryBM25Retriever]:
    """
    Initialize the Haystack document store and retriever.
    Returns the document store and retriever objects.
    """
    # Create a new document store
    document_store = InMemoryDocumentStore()

    # Initialize the retriever with BM25 algorithm
    retriever = InMemoryBM25Retriever(document_store=document_store)

    return document_store, retriever

# Function to index files
def index_files(files: List[str], base_dir: str) -> Tuple[int, List[str]]:
    """
    Index the given files into the document store.
    Returns the number of documents indexed and a list of errors if any.
    """
    if not st.session_state.search_document_store:
        doc_store, retriever = initialize_search_engine()
        st.session_state.search_document_store = doc_store
        st.session_state.search_retriever = retriever

    documents = []
    errors = []

    for file_path in files:
        # Skip already indexed files
        full_path = os.path.join(base_dir, file_path)
        if file_path in st.session_state.indexed_files:
            continue

        # Read file content
        content, error = read_file_content(full_path)
        if error:
            errors.append(f"Error with {file_path}: {error}")
            continue

        # For small files (< 4K), index as a single document
        if len(content) < 4000:
            documents.append(
                Document(
                    content=content,
                    meta={
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "is_snippet": False
                    }
                )
            )
        else:
            # For larger files, split into chunks
            chunks = split_by_paragraphs(content, file_path)
            documents.extend(chunks)

            # Also add the full document for "add entire file" option
            documents.append(
                Document(
                    content=content,
                    meta={
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "is_snippet": False
                    }
                )
            )

        # Mark file as indexed
        st.session_state.indexed_files.add(file_path)

    # Write documents to the document store
    if documents:
        st.session_state.search_document_store.write_documents(documents=documents)

    return len(documents), errors

# Function to search documents
def search_documents(query: str, top_k: int = 10) -> List[Document]:
    """
    Search for documents matching the query.
    Returns a list of Document objects.
    """
    if not st.session_state.search_retriever:
        return []

    # Create a proper filter structure according to Haystack documentation
    filters = {
        "operator": "==",
        "field": "meta.is_snippet",
        "value": True
    }

    # Perform search using the updated Haystack 2.x API
    results = st.session_state.search_retriever.run(
        query=query,
        top_k=top_k,
        filters=filters  # Updated filter format
    )

    # The retriever.run() method returns a dict with 'documents' key
    return results.get('documents', [])

# Function to format document content based on selected format
def format_document(name: str, content: str, format_type: str) -> str:
    """
    Format document content based on the selected format type.
    """
    if format_type == "xml":
        return f'<document name="{name}">\n{content}\n</document>'
    elif format_type == "markdown":
        # Try to determine language for syntax highlighting
        extension = pathlib.Path(name).suffix.lower()
        lang_map = {
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
        lang = lang_map.get(extension, '')

        return f'```{lang} {name}\n{content}\n```'
    elif format_type == "simple":
        return f'--- {name} ---\n{content}\n'
    else:
        return f'# {name}\n{content}\n'

# Function to add a search result to the selected list
def add_search_result(file_path: str, content: str, is_snippet: bool):
    """
    Add a search result to the selected items.
    """
    # Check if this exact content is already selected
    for doc in st.session_state.selected_search_results:
        if doc["path"] == file_path and doc["content"] == content:
            return  # Already selected

    # If adding entire file, remove any snippets from the same file
    if not is_snippet:
        st.session_state.selected_search_results = [
            doc for doc in st.session_state.selected_search_results 
            if doc["path"] != file_path
        ]

    # Add to selected documents with timestamp for ordering
    st.session_state.selected_search_results.append({
        "path": file_path,
        "content": content,
        "timestamp": datetime.now().timestamp(),
        "is_snippet": is_snippet
    })

# Function to remove a result from the selected list
def remove_search_result(index: int):
    """
    Remove a search result from the selected items by index.
    """
    if 0 <= index < len(st.session_state.selected_search_results):
        st.session_state.selected_search_results.pop(index)

def generate_preview() -> str:
    """
    Generate a preview of the selected search results in the chosen format.
    """
    if not st.session_state.selected_search_results:
        return "No documents selected."

    # Get format from config with fallback
    format_type = config.get_page_config_with_fallback("search", "format", "documents", "format", "xml")

    # Get instructions from config with fallback
    instructions = config.get_page_config_with_fallback(
        "search", 
        "instructions", 
        "documents", 
        "instructions",
        "I'm sharing some documents with you below. Please help me understand, analyze, "
        "or modify these documents based on my questions. Reference the document names "
        "when discussing specific parts."
    )

    preview = instructions + "\n\n"

    for doc in st.session_state.selected_search_results:
        # For snippets, include a note in the document name
        path = doc["path"]
        if doc["is_snippet"]:
            path = f"{path} (snippet)"

        preview += format_document(path, doc["content"], format_type) + "\n\n"

    return preview

# Function to get the full document content for a file
def get_full_document(file_path: str, base_dir: str) -> Tuple[str, Optional[str]]:
    """
    Get the full content of a document.
    Returns the content and an error message if any.
    """
    full_path = os.path.join(base_dir, file_path)
    return read_file_content(full_path)

# Main content
st.title("🔍 Search Documents")
st.markdown("Search for content in markdown files and add selected results to your chat.")

# Directory selection
col1, col2 = st.columns([3, 1])

with col1:
    base_folder = st.text_input(
        "Base Folder Path", 
        value=st.session_state.base_folder,
        help="Enter the folder path to search for markdown files"
    )

with col2:
    # Get recursive value from config with fallback
    default_recursive = config.get_page_config_with_fallback("search", "recursive", None, None, False)
    recursive = st.checkbox("Search Recursively", value=default_recursive)

    # Update config if changed
    if recursive != default_recursive:
        config.set_page_config("search", "recursive", recursive)

    # Get show_ignored_dirs value from config with fallback
    default_show_ignored = config.get_page_config_with_fallback("search", "show_ignored_dirs", None, None, False)
    show_ignored = st.checkbox("Show Ignored Directories", 
                              value=default_show_ignored,
                              help="Show files in directories that are normally ignored")

    # Update config if changed
    if show_ignored != default_show_ignored:
        config.set_page_config("search", "show_ignored_dirs", show_ignored)

# Update base folder in session state if changed
if base_folder != st.session_state.base_folder:
    st.session_state.base_folder = base_folder
    # Reset indexed files when changing directory
    st.session_state.indexed_files = set()
    st.session_state.search_document_store = None
    st.session_state.search_retriever = None

# Index files button
if st.button("Index Markdown Files", type="primary"):
    with st.spinner("Indexing markdown files..."):
        # List markdown files in the directory
        files, error = list_markdown_files(st.session_state.base_folder, recursive, show_ignored)

        if error:
            st.error(error)
        elif not files:
            st.info(f"No markdown files found in '{st.session_state.base_folder}'")
        else:
            # Index the files
            num_docs, errors = index_files(files, st.session_state.base_folder)

            # Show results
            if errors:
                for err in errors:
                    st.error(err)

            st.success(f"Indexed {num_docs} documents from {len(files)} markdown files.")

# Search interface
st.markdown("---")
st.subheader("Search")

col_query, col_count = st.columns([4, 1])

with col_query:
    search_query = st.text_input("Search Query", placeholder="Enter search terms...")

with col_count:
    # Get results count from config with fallback
    default_results_count = config.get_page_config_with_fallback("search", "results_count", None, None, 10)
    results_count = st.number_input(
        "Max Results", 
        min_value=1, 
        max_value=50, 
        value=default_results_count
    )

    # Update config if changed
    if results_count != default_results_count:
        config.set_page_config("search", "results_count", results_count)

# Search button
search_clicked = st.button("Search", type="primary", disabled=not search_query or not st.session_state.search_retriever)

# Store search query in session state if search is clicked
if search_clicked and search_query:
    st.session_state.last_search_query = search_query
    with st.spinner("Searching..."):
        results = search_documents(search_query, results_count)
        st.session_state.last_search_results = results  # Store results in session state

# Display search results (either from current search or from session state)
if st.session_state.last_search_results:
    results = st.session_state.last_search_results

    if not results:
        st.info("No results found. Try different search terms or index more files.")
    else:
        st.markdown(f"Found {len(results)} results for: **{st.session_state.last_search_query}**")

        # Display results
        for i, doc in enumerate(results):
            with st.container(border=True):
                # Extract metadata
                file_path = doc.meta.get("file_path", "Unknown file")
                is_snippet = doc.meta.get("is_snippet", True)

                # Display file path
                st.markdown(f"**{file_path}**")

                # Display content snippet with search term highlighting
                content = doc.content
                if len(content) > 500:
                    # Truncate long content for display
                    content = content[:500] + "..."

                # Very basic highlighting
                terms = st.session_state.last_search_query.split()
                highlighted_content = content
                for term in terms:
                    if len(term) > 2:  # Skip very short terms
                        pattern = re.compile(re.escape(term), re.IGNORECASE)
                        highlighted_content = pattern.sub(f"**{term}**", highlighted_content)

                st.markdown(highlighted_content)

                # Add buttons for adding snippet or full document
                col_snippet, col_full = st.columns(2)

                with col_snippet:
                    if st.button("Add Snippet", key=f"add_snippet_{i}"):
                        add_search_result(file_path, doc.content, True)
                        st.success(f"Added snippet from {file_path}")

                with col_full:
                    if st.button("Add Entire File", key=f"add_full_{i}"):
                        # Get full document content
                        full_content, error = get_full_document(file_path, st.session_state.base_folder)
                        if error:
                            st.error(error)
                        else:
                            add_search_result(file_path, full_content, False)
                            st.success(f"Added full document: {file_path}")

# Display selected items
st.markdown("---")
st.subheader("Selected Items")

if not st.session_state.selected_search_results:
    st.info("No items selected. Search and add items from the results.")
else:
    # Sort selected documents by selection time
    selected_items = sorted(st.session_state.selected_search_results, key=lambda x: x["timestamp"])

    # Display selected items with remove button
    for i, doc in enumerate(selected_items):
        with st.container(border=True):
            col_name, col_type, col_remove = st.columns([3, 1, 1])

            with col_name:
                st.write(f"{i+1}. {doc['path']}")
                st.caption(f"{len(doc['content'])} characters")

            with col_type:
                item_type = "Snippet" if doc["is_snippet"] else "Full Document"
                st.caption(item_type)

            with col_remove:
                if st.button("🗑️", key=f"remove_{i}", on_click=remove_search_result, args=(i,)):
                    pass  # Button action handled by on_click

    # Clear all button
    if st.button("Clear All Selected", type="secondary"):
        st.session_state.selected_search_results = []
        st.rerun()

# Document formatting options
st.markdown("---")
st.subheader("Document Formatting")

# Get format options from config with fallback
format_options = config.get_global("documents.format_options", {
    "xml": "XML Tags (<document name=\"filename\">content</document>)",
    "markdown": "Markdown (```filename\ncontent```)",
    "simple": "Simple Text (--- filename ---\ncontent)"
})

# Get current format from config with fallback
current_format = config.get_page_config_with_fallback("search", "format", "documents", "format", "xml")
selected_format = st.radio(
    "Select document format style:",
    options=list(format_options.keys()),
    format_func=lambda x: format_options.get(x, x),
    index=list(format_options.keys()).index(current_format) if current_format in format_options else 0,
    horizontal=True
)

# Update format in config if changed
if selected_format != current_format:
    # Update in both places to ensure consistency
    config.set_page_config("search", "format", selected_format)
    #config.set_global("documents.format", selected_format)

# Document instructions
st.subheader("Document Instructions")
st.caption("This text will be prepended to the documents when sending to the model")

# Get instructions from config with fallback
current_instructions = config.get_page_config_with_fallback(
    "search", 
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

# Update instructions in config if changed
if document_instructions != current_instructions:
    # Update in both places to ensure consistency
    config.set_page_config("search", "instructions", document_instructions)
    #config.set_global("documents.instructions", document_instructions)

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
    start_disabled = False
    if "selected_models" not in st.session_state or len(st.session_state.selected_models) == 0:
        start_disabled = True
        st.warning("You need to configure models before starting chat. Go to Model Selection first.")

    if st.button("Start Chat →", type="primary", disabled=start_disabled, use_container_width=True):
        if not start_disabled:
            # Transfer selected search results to the documents format expected by the chat
            if st.session_state.selected_search_results:
                # Clear any existing document selections
                st.session_state.selected_documents = []

                # Add search results as documents
                for item in st.session_state.selected_search_results:
                    st.session_state.selected_documents.append({
                        "path": item["path"] + (" (snippet)" if item["is_snippet"] else ""),
                        "content": item["content"],
                        "timestamp": item["timestamp"]
                    })

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
    st.title("Document Search")
    st.write("""
    This feature allows you to search through markdown files and include relevant content in your chat session.

    **How it works:**
    1. Index markdown files from the specified directory
    2. Search for specific content using keywords
    3. Select snippets or entire files from search results
    4. Configure formatting and start the chat session

    The selected content will be included in the first message to the AI.
    """)

    # Show search stats
    st.subheader("Search Statistics")

    # Document store stats
    doc_count = 0
    if st.session_state.search_document_store:
        doc_count = st.session_state.search_document_store.count_documents()

    st.metric("Indexed Documents", doc_count)
    st.metric("Selected Items", len(st.session_state.selected_search_results))

    # Estimate token count for selected items
    total_chars = sum(len(doc["content"]) for doc in st.session_state.selected_search_results)
    est_tokens = total_chars // 4  # Rough estimate: ~4 chars per token

    st.metric("Estimated Tokens", est_tokens)

    if est_tokens > 8000:
        st.warning("⚠️ Selected content may exceed context limits of some models.")

    # Reset search index button
    if st.button("Reset Search Index", type="secondary"):
        st.session_state.search_document_store = None
        st.session_state.search_retriever = None
        st.session_state.indexed_files = set()
        st.success("Search index has been reset. You'll need to re-index files.")

    # Advanced settings expander for ignored directories
    with st.expander("Advanced Settings"):
        st.subheader("Ignored Directories")
        st.caption("These directories are skipped when browsing files")

        # Get ignored directories from config
        ignored_dirs_list = config.get_global("ignored_directories", [])
        ignored_dirs_text = st.text_area(
            "One directory name per line:", 
            value="\n".join(sorted(ignored_dirs_list)),
            height=150
        )

        # Update the ignored directories if changed
        if st.button("Update Ignored Directories"):
            # Split by newlines and filter out empty lines
            new_ignored_dirs = [dir.strip() for dir in ignored_dirs_text.split("\n") if dir.strip()]
            config.set_global("ignored_directories", new_ignored_dirs)
            st.success("Ignored directories updated!")