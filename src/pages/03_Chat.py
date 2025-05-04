# pages/03_Chat.py

import streamlit as st
import os
from haystack.dataclasses import ChatMessage
from haystack_integrations.components.generators.amazon_bedrock import AmazonBedrockChatGenerator
from haystack_integrations.components.generators.ollama import OllamaChatGenerator

# Set page configuration
st.set_page_config(
    page_title="Chat - Haystack Multi-LLM Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Get the ConfigManager instance
config = st.session_state.config_manager

# Check if we have selected models
if "selected_models" not in st.session_state or not st.session_state.selected_models:
    st.error("No models are selected. Please configure models first.")
    if st.button("Go to Model Selection", type="primary"):
        st.switch_page("pages/01_Model_Selection.py")
    st.stop()

# Helper functions for document formatting
def format_document(name, content, format_type):
    """Format a document based on the selected format style."""
    if format_type == "xml":
        return f'<document name="{name}">\n{content}\n</document>'
    elif format_type == "markdown":
        # Try to determine language for syntax highlighting
        extension = os.path.splitext(name)[1].lower()
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

def prepare_document_context():
    """Prepare document context text if documents are selected."""
    if not st.session_state.get("selected_documents"):
        return None

    # Get document format from config (with fallback to session state for backward compatibility)
    format_type = config.get_page_config("documents", "format", "xml")

    # Get document instructions from config (with fallback to session state for backward compatibility)
    instructions = config.get_global("documents", {}).get("instructions", "")

    # Start with instructions
    context = instructions + "\n\n"

    # Add each document with proper formatting
    for doc in st.session_state.get("selected_documents", []):
        context += format_document(doc["path"], doc["content"], format_type) + "\n\n"

    return context

# Helper functions for chat management
def get_user_and_selected_responses():
    """Get chat history with responses from user and selected assistant message"""
    # Start with the system message if set
    user_and_selected_messages = []

    # Get system prompt from config
    system_prompt = config.get_global("system_prompt", "")

    # Add system prompt if available
    if system_prompt.strip():
        system_message = ChatMessage.from_system(system_prompt)
        user_and_selected_messages.append(system_message)

    # Then add user messages and selected assistant responses
    for msg in st.session_state.messages:
        if msg.role.value == "user" or msg.meta.get("selected", True):
            user_and_selected_messages.append(msg)

    return user_and_selected_messages

def get_responses_for_user_message(user_msg_idx):
    """Get all model responses for a specific user message."""
    responses = []
    i = user_msg_idx + 1
    while i < len(st.session_state.messages) and st.session_state.messages[i].role.value == "assistant":
        responses.append(st.session_state.messages[i])
        i += 1
    return responses

def display_usage_statistics():
    # Add usage statistics display
    with st.expander("Usage Statistics", expanded=True):
        for model in st.session_state.selected_models:
            model_name = model["name"]
            provider = model["provider"]

            st.write(f"**{model_name}** ({provider})")

            # Check if we have usage statistics for this model
            if "usage_stats" in model and model["usage_stats"]["response_count"] > 0:
                stats = model["usage_stats"]

                # Calculate average tokens per second
                avg_tps = "N/A"
                if stats["total_output_tokens"] > 0 and stats["total_eval_duration_ns"] > 0:
                    eval_duration_seconds = stats["total_eval_duration_ns"] / 1_000_000_000
                    avg_tps = f"{stats['total_output_tokens'] / eval_duration_seconds:.2f}"

                st.write(f"Total Input Tokens: {stats['total_input_tokens']}")
                st.write(f"Total Output Tokens: {stats['total_output_tokens']}")
                st.write(f"Average Speed: {avg_tps} tokens/sec")
            else:
                st.write("No usage data available yet.")

def reset_chat():
    """Reset the chat history."""
    st.session_state.messages = []
    st.session_state.last_user_msg_idx = -1
    if "awaiting_selection" in st.session_state:
        del st.session_state.awaiting_selection

    # Reset model usage statistics
    if "selected_models" in st.session_state:
        for model in st.session_state.selected_models:
            if "usage_stats" in model:
                del model["usage_stats"]

# This function extracts standardized token usage from response metadata
def extract_token_usage(metadata):
    """
    Extract token usage information from response metadata.

    Args:
        metadata (dict): The metadata from the LLM response

    Returns:
        dict: Dictionary with token usage information or None if not available
    """
    # Check if the response is complete
    if not metadata.get("done", True):
        return None

    # Try to get usage information
    usage = metadata.get("usage", {})

    # If no usage information is available
    if not usage:
        return None

    # Extract token counts
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    # Extract evaluation duration
    eval_duration_ns = metadata.get("eval_duration", 0)

    # Calculate tokens per second if we have both tokens and duration
    tokens_per_second = None
    if output_tokens > 0 and eval_duration_ns > 0:
        eval_duration_seconds = eval_duration_ns / 1_000_000_000
        tokens_per_second = output_tokens / eval_duration_seconds

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "eval_duration_ns": eval_duration_ns,
        "tokens_per_second": tokens_per_second
    }

# Function to update model usage statistics
def update_model_usage_stats(model_id, usage_info):
    """
    Update the usage statistics for a specific model.

    Args:
        model_id (str): The ID of the model
        usage_info (dict): The usage information to add
    """
    if not usage_info:
        return

    # Find the model in selected_models
    for model in st.session_state.selected_models:
        if model["id"] == model_id:
            # Initialize usage_stats if it doesn't exist
            if "usage_stats" not in model:
                model["usage_stats"] = {
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_eval_duration_ns": 0,
                    "response_count": 0
                }

            # Update the statistics
            model["usage_stats"]["total_input_tokens"] += usage_info["input_tokens"]
            model["usage_stats"]["total_output_tokens"] += usage_info["output_tokens"]
            model["usage_stats"]["total_eval_duration_ns"] += usage_info["eval_duration_ns"]
            model["usage_stats"]["response_count"] += 1
            break

# Initialize session state for chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Track the last user message index for grouping responses
if "last_user_msg_idx" not in st.session_state:
    st.session_state.last_user_msg_idx = -1

# Initialize LLM generators for each selected model
@st.cache_resource(show_spinner=False)
def get_generator(model):
    """Initialize and return the appropriate generator based on model config."""
    provider = model["provider"]
    model_name = model["name"]
    params = model["params"]

    if provider == "AWS Bedrock":
        # Get AWS region from config with fallback to model params
        region = config.get_provider_config("bedrock", "region", params.get("region", "us-east-1"))
        os.environ["AWS_REGION"] = region

        # Create generator with streaming capability
        def streaming_callback(chunk):
            st.session_state[f"streaming_{model['id']}"].append(chunk.content)
            st.session_state[f"placeholder_{model['id']}"].markdown("".join(st.session_state[f"streaming_{model['id']}"]))

        return AmazonBedrockChatGenerator(
            model=model_name,
            generation_kwargs=params,
            streaming_callback=streaming_callback
        )

    elif provider == "Ollama":
        # Extract Ollama-specific parameters with config fallback
        url = model.get("url", config.get_provider_config("ollama", "url", "http://localhost:11434"))

        # Create generator with streaming capability
        def streaming_callback(chunk):
            st.session_state[f"streaming_{model['id']}"].append(chunk.content)
            st.session_state[f"placeholder_{model['id']}"].markdown("".join(st.session_state[f"streaming_{model['id']}"]))

        return OllamaChatGenerator(
            model=model_name,
            url=url,
            generation_kwargs=params,
            timeout=300,    # Longer timeout
            streaming_callback=streaming_callback
        )

    return None

# Main chat interface
st.title("💬 Haystack Multi-LLM Chat")

# Display model information in the sidebar
with st.sidebar:
    st.title("Active Models")

    # Add container so usage information can be added later
    usage_container = st.empty()
    with usage_container:
        display_usage_statistics()

    for model in st.session_state.selected_models:
        with st.expander(f"{model['name']} ({model['provider']})"):
            # Show model parameters
            for key, value in model["params"].items():
                st.write(f"**{key}:** {value}")

            # Show provider-specific info
            if model["provider"] == "Ollama":
                st.write(f"**URL:** {model['url']}")

    # Add system prompt display
    with st.expander("System Prompt"):
        # Get system prompt from config
        system_prompt = config.get_global("system_prompt", "")

        if system_prompt.strip():
            st.text_area(
                "Current system prompt:", 
                value=system_prompt,
                height=150,
                disabled=True
            )
        else:
            st.info("No system prompt set.")

    # Add document information display
    if st.session_state.get("selected_documents"):
        with st.expander("Documents", expanded=True):
            st.write(f"**{len(st.session_state.selected_documents)} document(s) included:**")
            for doc in st.session_state.selected_documents:
                st.write(f"- {doc['path']}")

            # Get format from config
            doc_format = config.get_page_config("documents", "format", "xml")
            st.write(f"**Format:** {doc_format}")

            # Add button to view document preview
            if st.button("View Document Preview"):
                # Prepare preview text
                preview = prepare_document_context()
                if preview:
                    st.code(preview[:500] + "..." if len(preview) > 500 else preview)

    # Add reset chat button
    if st.button("Reset Chat", type="secondary", use_container_width=True):
        reset_chat()
        st.rerun()

    # Add back to model selection button
    if st.button("← Back to Model Selection", use_container_width=True):
        st.switch_page("pages/01_Model_Selection.py")

    # Add back to document selection button
    if st.session_state.get("selected_documents"):
        if st.button("← Back to Documents", use_container_width=True):
            st.switch_page("pages/02_Documents.py")

# Display chat messages with side-by-side model responses
user_msg_idx = -1
i = 0
selection_made_for_last_message = False

while i < len(st.session_state.messages):
    msg = st.session_state.messages[i]

    # Display user message
    if msg.role.value == "user":
        user_msg_idx = i
        with st.chat_message("user"):
            st.write(msg.text)

        # Get all assistant responses for this user message
        responses = get_responses_for_user_message(user_msg_idx)

        if responses:
            # Create columns for side-by-side display
            cols = st.columns(len(responses))

            # Track if this is the last user message
            is_last_user_message = (user_msg_idx == st.session_state.last_user_msg_idx)

            # Check if any response is selected for this message
            any_selected = any(r.meta.get("selected", False) for r in responses)

            # If this is the last message and we're awaiting selection, we need to enforce it
            require_selection = is_last_user_message and "awaiting_selection" in st.session_state

            # If this is the last message, track if a selection has been made
            if is_last_user_message:
                selection_made_for_last_message = any_selected

            # Display each response in its own column
            for j, (response, col) in enumerate(zip(responses, cols)):
                with col:
                    model_name = response.meta.get("model_name", "Unknown Model")
                    provider = response.meta.get("provider", "Unknown Provider")
                    st.subheader(f"{model_name}")
                    st.caption(f"Provider: {provider}")
                    st.write(response.text)

                    # Selection radio button (only show if we have multiple models)
                    if len(responses) > 1:
                        is_selected = st.radio(
                            "Select this response" + (" (required)" if require_selection else ""),
                            ["No", "Yes"],
                            index=1 if response.meta.get("selected", False) else 0,
                            key=f"select_{user_msg_idx}_{j}",
                            horizontal=True
                        ) == "Yes"

                        # Update selection state if changed
                        if is_selected != response.meta.get("selected", False):
                            # Deselect all responses for this user message
                            if is_selected:
                                for r in responses:
                                    r.meta["selected"] = False
                            # Select this response
                            response.meta["selected"] = is_selected

                            # If this is the last message and we made a selection, clear the awaiting flag
                            if is_last_user_message and is_selected:
                                if "awaiting_selection" in st.session_state:
                                    del st.session_state.awaiting_selection
                                    st.rerun()  # Force a rerun to update the UI

        # Skip over the assistant responses we just displayed
        i += len(responses) + 1
    else:
        i += 1

# If we're still awaiting selection for the last message, show a warning
if "awaiting_selection" in st.session_state and not selection_made_for_last_message:
    st.warning("⚠️ Please select one response before continuing.")

# Add this section before the chat input to display persistent messages
# Display help or warning messages if they exist in session state
if "show_chat_help_message" in st.session_state and st.session_state.show_chat_help_message:
    with st.expander("Help - Available Slash Commands", expanded=True):
        st.markdown("""
        - `/help` - Show this help message
        - `/retry` - Retry the last message with all models
        """)
        if st.button("Dismiss"):
            del st.session_state.show_chat_help_message
            st.rerun()

# Chat input
if prompt := st.chat_input("What would you like to ask? Help is available with /help", disabled="awaiting_selection" in st.session_state):
    # Handle slash commands
    if prompt == "/help":
        st.session_state.show_chat_help_message = True
        st.rerun()
    elif prompt == "/retry":
        pass # resend chat history without adding new messages
    else:
        # Check if this is the first message and we have documents
        is_first_message = len(st.session_state.messages) == 0
        document_context = prepare_document_context() if is_first_message else None

        # If we have documents, prepend them to the first message
        user_text = prompt
        if document_context:
            user_text = f"{document_context}\n\n{prompt}"

        # Create a user message with metadata and add to history
        user_message = ChatMessage.from_user(user_text, meta={"selected": True})
        st.session_state.messages.append(user_message)
        st.session_state.last_user_msg_idx = len(st.session_state.messages) - 1

        # Display user message (but only show the original prompt, not the document context)
        with st.chat_message("user"):
            if document_context:
                st.caption("Documents included with this message")
            st.write(prompt)

    # Get the conversation history once for all models
    user_and_selected_messages = get_user_and_selected_responses()

    # Create columns for all models at once
    cols = st.columns(len(st.session_state.selected_models))

    # Set the default selection state for responses
    default_selection_state = True  # One model
    if len(st.session_state.selected_models) > 1:
        default_selection_state = False # More than one model

    # Process with each selected model
    for model_idx, model_info in enumerate(st.session_state.selected_models):
        provider = model_info["provider"]
        model_name = model_info["name"]
        model_id = model_info["id"]

        # Initialize streaming buffer for this model
        st.session_state[f"streaming_{model_id}"] = []

        # Use the pre-created column for this model
        with cols[model_idx]:
            st.subheader(f"{model_name}")
            st.caption(f"Provider: {provider}")

            # Create a placeholder for streaming text
            response_placeholder = st.empty()

            # Store placeholder in session state for streaming callback to use
            st.session_state[f"placeholder_{model_id}"] = response_placeholder

            try:
                # Get the generator for this model
                generator = get_generator(model_info)

                # Generate response using the same filtered history for all models
                response = generator.run(messages=user_and_selected_messages)

                # Get the response message
                response_message = response["replies"][0]  # This is a ChatMessage object
                response_text = response_message.text

                # Extract metadata from the response_message
                metadata = response_message.meta or {}

                # Extract token usage information
                usage_info = extract_token_usage(metadata)

                # Update model usage statistics
                if usage_info:
                    update_model_usage_stats(model_id, usage_info)

                # Create metadata dictionary - all responses start as unselected
                meta = {
                    "model_name": model_name,
                    "provider": provider,
                    "selected": default_selection_state,
                    "model_id": model_id
                }

                # Add usage information to metadata if available
                if usage_info:
                    meta["usage_info"] = usage_info

                # Create the message with metadata
                chat_message = ChatMessage.from_assistant(
                    response_text,
                    meta=meta
                )

                # Add assistant response to chat history
                st.session_state.messages.append(chat_message)

                # Display usage statistics below the response if available
                if usage_info and usage_info["tokens_per_second"] is not None:
                    st.caption(
                        f"Input: {usage_info['input_tokens']} tokens | "
                        f"Output: {usage_info['output_tokens']} tokens | "
                        f"Speed: {usage_info['tokens_per_second']:.2f} tokens/sec"
                    )
                elif usage_info:
                    st.caption(
                        f"Input: {usage_info['input_tokens']} tokens | "
                        f"Output: {usage_info['output_tokens']} tokens"
                    )

            except Exception as e:
                error_message = f"Error generating response: {str(e)}"
                # Check specifically for AWS Bedrock throttling exceptions
                if "ThrottlingException" in str(e) and "ConverseStream" in str(e):
                    error_message = (
                        f"⚠️ AWS Bedrock throttling error occurred with {model_name}: {str(e)}\n\n"
                        "Please try again by typing `/retry` in the chat input."
                    )
                response_placeholder.error(error_message)

    # Update usage statistics
    with usage_container:
        display_usage_statistics()

    # After all responses are generated, set flag to require selection
    if len(st.session_state.selected_models) > 1:  # Only require selection if we have multiple models
        st.session_state.awaiting_selection = True
        st.warning("⚠️ Please select one response before continuing.")
        # Force a rerun to update the UI with the disabled chat input
        st.rerun()
