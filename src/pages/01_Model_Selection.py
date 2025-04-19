# pages/01_Model_Selection.py

import streamlit as st
import requests
import boto3
import time
import os
from functools import partial

# Set page configuration
st.set_page_config(
    page_title="Configure Models - Haystack Multi-LLM Chat",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Get the ConfigManager instance
config = st.session_state.config_manager

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_ollama_models(ollama_url="http://localhost:11434"):
    """Query Ollama for available models."""
    try:
        response = requests.get(f"{ollama_url}/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])

            # Create a list of model information dictionaries
            model_info_list = []

            for model in models:
                name = model["name"]
                display_name = name

                # Extract parameter size and quantization if available
                if "details" in model:
                    param_size = model["details"].get("parameter_size", "")
                    quant_level = model["details"].get("quantization_level", "")

                    # Add parameter size and quantization to display name if available
                    if param_size or quant_level:
                        display_info = []
                        if param_size:
                            display_info.append(param_size)
                        if quant_level:
                            display_info.append(quant_level)
                        display_name = f"{name} ({', '.join(display_info)})"

                model_info_list.append({
                    "name": name,           # Original name for API calls
                    "display_name": display_name,  # Enhanced name for display
                    "details": model.get("details", {})
                })

            # Sort the model list alphabetically by display_name
            model_info_list = sorted(model_info_list, key=lambda x: x["display_name"].lower())

            return model_info_list
        else:
            st.warning(f"Failed to fetch Ollama models: {response.status_code}")
            return [{"name": "gemma3:27b", "display_name": "gemma3:27b"}]  # Default fallback
    except Exception as e:
        st.warning(f"Error connecting to Ollama: {str(e)}")
        return [{"name": "gemma3:27b", "display_name": "gemma3:27b"}]  # Default fallback

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_bedrock_models(region="us-east-1"):
    """Query AWS Bedrock for available models."""
    try:
        # Get region from config if available
        region = config.get_provider_config("bedrock", "region", region)

        # Initialize Bedrock client with specified region
        bedrock_client = boto3.client('bedrock', region_name=region)

        # Get list of foundation models
        response = bedrock_client.list_foundation_models()

        # Filter for text generation models that support chat
        chat_models = []
        for model in response.get('modelSummaries', []):
            # Check if model supports text generation and is available
            if ('text' in model.get('inputModalities', []) and 
                'text' in model.get('outputModalities', []) and
                model.get('modelLifecycle', {}).get('status') == 'ACTIVE'):
                chat_models.append(model['modelId'])

        # If no models found, return default
        if not chat_models:
            return ["us.anthropic.claude-3-7-sonnet-20250219-v1:0"]

        return chat_models
    except Exception as e:
        st.warning(f"Error fetching AWS Bedrock models: {str(e)}")
        return ["us.anthropic.claude-3-7-sonnet-20250219-v1:0"]  # Default fallback

# Initialize selected models in session state if not already present
# We keep this in session state as it represents application state, not configuration
if "selected_models" not in st.session_state:
    st.session_state.selected_models = []

# Initialize form reset flag
if "reset_form" not in st.session_state:
    st.session_state.reset_form = False

# Function to add a model to the selected list
def add_model(provider, model_name, params):
    # Create a unique ID for the model
    model_id = f"{provider}_{model_name}_{time.time()}"

    # Create model config dictionary
    model_config = {
        "id": model_id,
        "provider": provider,
        "name": model_name,
        "params": params
    }

    # Add provider-specific parameters
    if provider == "Ollama":
        model_config["url"] = params.pop("url", "http://localhost:11434")

    # Add to session state
    st.session_state.selected_models.append(model_config)

    # Set flag to reset the form on next rerun
    st.session_state.reset_form = True
    st.rerun()

# Function to remove a model from the selected list
def remove_model(model_id):
    st.session_state.selected_models = [
        model for model in st.session_state.selected_models 
        if model["id"] != model_id
    ]

# Main content
st.title("🔧 Configure Models")
st.markdown("Select and configure the models you want to compare in your chat session.")

# Create two columns for the layout
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("Add New Model")

    # If we need to reset the form
    if st.session_state.reset_form:
        # Reset the flag
        st.session_state.reset_form = False
        # We can't reset widgets directly, but the form will show empty values on next run

    # Provider selection
    # Use config to get the default provider
    default_provider = config.get_page_config("model_selection", "default_provider", "")
    provider_options = ["", "AWS Bedrock", "Ollama"]
    provider = st.selectbox(
        "Select Provider", 
        provider_options,
        index=provider_options.index(default_provider) if default_provider in provider_options else 0,
        key="new_model_provider"
    )

    # Save the selected provider as default
    if provider != default_provider and provider != "":
        config.set_page_config("model_selection", "default_provider", provider)

    if provider:
        # Provider-specific configuration
        if provider == "AWS Bedrock":
            # AWS Region - get from provider config
            aws_region = st.text_input(
                "AWS Region", 
                value=config.get_provider_config("bedrock", "region", "us-east-1")
            )

            # Update provider config if region changed
            if aws_region != config.get_provider_config("bedrock", "region", "us-east-1"):
                config.set_provider_config("bedrock", "region", aws_region)

            # Get available models
            with st.spinner("Loading AWS Bedrock models..."):
                bedrock_models = get_bedrock_models(region=aws_region)

            # Model selection
            model_name = st.selectbox(
                "Select Model", 
                [""] + bedrock_models,
                key="new_model_name"
            )

            if model_name:
                # Get default parameters from config
                default_max_tokens = config.get_provider_config("bedrock", "default_max_tokens", 4000)
                default_temperature = config.get_provider_config("bedrock", "default_temperature", 0.7)

                # Model parameters
                with st.expander("Model Parameters", expanded=True):
                    max_tokens = st.slider("Max Tokens", min_value=100, max_value=8000, value=default_max_tokens, step=100)
                    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=default_temperature, step=0.1)

                # Add model button
                if st.button("Add Model", type="primary"):
                    params = {
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                    add_model("AWS Bedrock", model_name, params)

                    # Save defaults if they changed
                    if max_tokens != default_max_tokens:
                        config.set_provider_config("bedrock", "default_max_tokens", max_tokens)
                    if temperature != default_temperature:
                        config.set_provider_config("bedrock", "default_temperature", temperature)

        elif provider == "Ollama":
            # Ollama URL - get from provider config
            default_url = config.get_provider_config("ollama", "url", "http://localhost:11434")
            ollama_url = st.text_input("Ollama Server URL", value=default_url)

            # Update provider config if URL changed
            if ollama_url != default_url:
                config.set_provider_config("ollama", "url", ollama_url)

            # Get available models
            with st.spinner("Loading Ollama models..."):
                ollama_models = get_ollama_models(ollama_url)

            # Create a list of display names for the dropdown
            display_names = [""] + [model["display_name"] for model in ollama_models]

            # Model selection
            selected_display_name = st.selectbox(
                "Select Model", 
                display_names,
                key="new_model_display_name"
            )

            if selected_display_name:
                # Find the selected model in our list
                selected_model = next((model for model in ollama_models 
                                    if model["display_name"] == selected_display_name), None)

                if selected_model:
                    model_name = selected_model["name"]  # Get the actual model name for API calls

                    # Get default parameters from config
                    default_max_tokens = config.get_provider_config("ollama", "default_max_tokens", 4000)
                    default_temperature = config.get_provider_config("ollama", "default_temperature", 0.7)
                    default_context_window = config.get_provider_config("ollama", "default_context_window", 64000)

                    # Model parameters
                    with st.expander("Model Parameters", expanded=True):
                        max_tokens = st.slider("Max Tokens", min_value=100, max_value=8000, value=default_max_tokens, step=100)
                        temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=default_temperature, step=0.1)
                        context_window = st.slider("Context Window Size", min_value=1000, max_value=128000, value=default_context_window, step=1000)

                    # Add model button
                    if st.button("Add Model", type="primary"):
                        params = {
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                            "num_ctx": context_window
                        }
                        # Store the display name for showing in the selected models list
                        add_model("Ollama", model_name, {"url": ollama_url, "display_name": selected_display_name, **params})

                        # Save defaults if they changed
                        if max_tokens != default_max_tokens:
                            config.set_provider_config("ollama", "default_max_tokens", max_tokens)
                        if temperature != default_temperature:
                            config.set_provider_config("ollama", "default_temperature", temperature)
                        if context_window != default_context_window:
                            config.set_provider_config("ollama", "default_context_window", context_window)

# Right column - Selected models
with col2:
    st.subheader("Selected Models")

    if not st.session_state.selected_models:
        st.info("No models selected yet. Add at least one model to continue.")
    else:
        for i, model in enumerate(st.session_state.selected_models):
            with st.container(border=True):
                col_info, col_remove = st.columns([4, 1])

                with col_info:
                    # Use display_name if available, otherwise use name
                    display_name = model.get("params", {}).get("display_name", model["name"]) if model["provider"] == "Ollama" else model["name"]
                    st.subheader(display_name)
                    st.caption(f"Provider: {model['provider']}")

                    # Display parameters
                    st.write("Parameters:")
                    # Filter out display_name from params to avoid showing it twice
                    params_to_show = {k: v for k, v in model["params"].items() if k != "display_name"} if model["provider"] == "Ollama" else model["params"]
                    for key, value in params_to_show.items():
                        st.write(f"- {key}: {value}")

                    # Display provider-specific info
                    if model["provider"] == "Ollama":
                        st.write(f"- URL: {model['url']}")

                with col_remove:
                    st.button("🗑️", key=f"remove_{model['id']}", 
                              on_click=partial(remove_model, model["id"]))

        # Clear all button
        if st.button("Clear All Models", type="secondary"):
            st.session_state.selected_models = []
            st.rerun()

# After the selected models section, before the navigation section
st.markdown("---")  # This is the dashed line you mentioned

# System prompt configuration
st.subheader("System Prompt")
st.caption("This prompt will be sent to all models to define their behavior.")

# Get system prompt from global config
system_prompt = st.text_area(
    "System Prompt",
    value=config.get_global("system_prompt", 
        "You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should be detailed, accurate, and relevant to the question. If a question doesn't make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information."),
    height=150,
    help="This instruction sets how all models will behave in the conversation."
)

# Update global config when the prompt changes
if system_prompt != config.get_global("system_prompt", ""):
    config.set_global("system_prompt", system_prompt)
    st.success("System prompt updated!")

# Disable the button if no models are selected
start_disabled = len(st.session_state.selected_models) == 0

# Navigation buttons
col_back, col_spacer, col_next, col_docs = st.columns([1, 1, 1, 1])

with col_back:
    if st.button("← Back to Home", type="secondary", use_container_width=True):
        st.switch_page("app.py")

with col_next:
    if st.button("Start Chat →", type="primary", disabled=start_disabled, use_container_width=True):
        if len(st.session_state.selected_models) > 0:
            # Initialize/reset chat history
            st.session_state.messages = []
            st.session_state.last_user_msg_idx = -1
            if "awaiting_selection" in st.session_state:
                del st.session_state.awaiting_selection

            # Navigate to chat page
            st.switch_page("pages/03_Chat.py")
        else:
            st.error("Please add at least one model before starting chat.")

with col_docs:
    if st.button("Select Documents →", type="primary", disabled=start_disabled, use_container_width=True):
        if len(st.session_state.selected_models) > 0:
            # Navigate to documents page
            st.switch_page("pages/02_Documents.py")
        else:
            st.error("Please add at least one model before selecting documents.")

# Sidebar with refresh options
with st.sidebar:
    st.title("Refresh Model Lists")

    if st.button("Refresh AWS Bedrock Models"):
        st.cache_data.clear()
        st.success("AWS Bedrock model list refreshed")
        st.rerun()

    if st.button("Refresh Ollama Models"):
        st.cache_data.clear()
        st.success("Ollama model list refreshed")
        st.rerun()