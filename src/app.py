# app.py (Main page)
# Haystack Multi-LLM Chat
# Copyright (C) 2025 DigitalReplica
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# See the LICENSE file for the full license text.

import streamlit as st
import yaml
from datetime import datetime
from utils.config_manager import ConfigManager

# Set page configuration
st.set_page_config(
    page_title="Haystack Multi-LLM Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize configuration manager (only once at startup)
if "config_manager" not in st.session_state:
    st.session_state.config_manager = ConfigManager()

# Initialize session state variables for configuration management
# UPDATED: Always refresh yaml_editor_content with current config
st.session_state.yaml_editor_content = yaml.dump(
    st.session_state.config_manager.get_config(), 
    sort_keys=False, 
    default_flow_style=False
)
if "yaml_valid" not in st.session_state:
    st.session_state.yaml_valid = True
if "yaml_error" not in st.session_state:
    st.session_state.yaml_error = ""
if "selected_template_name" not in st.session_state:
    st.session_state.selected_template_name = "New template..."
if "new_template_name" not in st.session_state:
    st.session_state.new_template_name = ""
if "template_description" not in st.session_state:
    st.session_state.template_description = ""

# Main content
st.title("🤖 Haystack Multi-LLM Chat")
st.markdown("### Compare responses from multiple language models side-by-side")

# Introduction in expander
with st.expander("ℹ️ About this application", expanded=False):
    st.markdown("""
    This application allows you to:
    - Select and configure multiple LLM providers and models
    - Chat with all selected models simultaneously
    - Compare responses side-by-side
    - Build a conversation history from your preferred responses

    ## How it works

    1. **Configure Models**: Start by selecting which models you want to compare
    2. **Chat Interface**: Ask questions and see responses from all models
    3. **Select Best Responses**: Choose which model's response you prefer for each question
    4. **Build Conversation**: All models will see the same conversation history based on your selections

    ## Supported Providers

    - **AWS Bedrock**: Access Amazon's foundation models (requires AWS credentials)
    - **Ollama**: Use locally running or remote Ollama models
    """)

# Configuration Management Section
st.markdown("## Configuration Management")

# Helper functions for YAML validation
def validate_yaml(yaml_content):
    try:
        yaml.safe_load(yaml_content)
        st.session_state.yaml_valid = True
        st.session_state.yaml_error = ""
        return True
    except Exception as e:
        st.session_state.yaml_valid = False
        st.session_state.yaml_error = str(e)
        return False

def update_yaml_editor():
    st.session_state.yaml_editor_content = yaml.dump(
        st.session_state.config.get_config(), 
        sort_keys=False, 
        default_flow_style=False
    )

def apply_yaml_changes():
    if validate_yaml(st.session_state.yaml_editor_content):
        st.session_state.config = yaml.safe_load(st.session_state.yaml_editor_content)
        return True
    return False

# 1. Configuration Viewer/Editor Section
st.markdown("### Current Configuration")
yaml_content = st.text_area(
    "Edit configuration (YAML format)",
    value=st.session_state.yaml_editor_content,
    height=300,
    key="yaml_editor"
)

# Update session state when text area changes
if yaml_content != st.session_state.yaml_editor_content:
    st.session_state.yaml_editor_content = yaml_content

col1, col2 = st.columns(2)
with col1:
    if st.button("Validate YAML", use_container_width=True):
        if validate_yaml(st.session_state.yaml_editor_content):
            st.success("YAML syntax is valid.")
        else:
            st.error(f"YAML syntax error: {st.session_state.yaml_error}")

with col2:
    if st.button("Apply Changes", use_container_width=True):
        if apply_yaml_changes():
            st.success("Configuration updated successfully!")
        else:
            st.error(f"Failed to apply changes: {st.session_state.yaml_error}")

# 2. Application Configuration Management
st.markdown("### Application Configuration")
app_col1, app_col2 = st.columns(2)

with app_col1:
    if st.button("Load App Config", use_container_width=True):
        if st.session_state.config_manager.load_app_config():
            # Update the config in session state
            st.session_state.config = st.session_state.config_manager.get_config()
            # Update the YAML editor content with the loaded configuration
            st.session_state.yaml_editor_content = yaml.dump(
                st.session_state.config,
                sort_keys=False,
                default_flow_style=False
            )
            st.success("Application configuration loaded successfully!")
            st.rerun()  # Force a rerun to update the UI
        else:
            st.error("Failed to load application configuration.")

with app_col2:
    if st.button("Save as App Config", use_container_width=True):
        # First apply any pending changes from the editor
        if apply_yaml_changes():
            if st.session_state.config_manager.save_app_config():
                st.success("Configuration saved as application default!")
            else:
                st.error("Failed to save application configuration.")
        else:
            st.error(f"Cannot save invalid configuration: {st.session_state.yaml_error}")

# 3. Template Management
st.markdown("### Template Management")

# Get list of templates
templates = st.session_state.config_manager.list_templates()
template_names = ["New template..."] + [t["template_name"] for t in templates]

# Template selection
selected_template = st.selectbox(
    "Select template", 
    template_names,
    index=template_names.index(st.session_state.selected_template_name) if st.session_state.selected_template_name in template_names else 0,
    key="template_selector"
)

# Update the selected template in session state when it changes
if selected_template != st.session_state.selected_template_name:
    st.session_state.selected_template_name = selected_template

# Description field
if selected_template == "New template...":
    # For new template, show name field and description
    new_template_name = st.text_input(
        "New template name",
        value=st.session_state.new_template_name,
        key="new_template_name"
    )
    if new_template_name != st.session_state.new_template_name:
        st.session_state.new_template_name = new_template_name

    template_description = st.text_input(
        "Description",
        value=st.session_state.template_description,
        key="template_description"
    )
    if template_description != st.session_state.template_description:
        st.session_state.template_description = template_description
else:
    # For existing template, show its description if available
    template_metadata = next((t for t in templates if t["template_name"] == selected_template), {})
    template_description = template_metadata.get("description", "")
    st.text_input("Description", value=template_description, disabled=True)

# Template operations
template_col1, template_col2 = st.columns(2)

with template_col1:
    load_disabled = selected_template == "New template..."
    if st.button("Load Template", disabled=load_disabled, use_container_width=True):
        if st.session_state.config_manager.load_template(selected_template):
            # Update the YAML editor content with the loaded configuration
            st.session_state.yaml_editor_content = yaml.dump(
                st.session_state.config,
                sort_keys=False,
                default_flow_style=False
            )
            # Remember this template as the currently active one
            st.session_state.selected_template_name = selected_template
            st.success(f"Template '{selected_template}' loaded successfully!")
            st.rerun()  # Force a rerun to update the UI
        else:
            st.error(f"Failed to load template '{selected_template}'.")

with template_col2:
    if selected_template == "New template...":
        # Create new template
        create_disabled = not st.session_state.new_template_name or not st.session_state.yaml_valid
        if st.button("Create Template", disabled=create_disabled, use_container_width=True):
            # First apply any pending changes from the editor
            if apply_yaml_changes():
                # Pass the current datetime to avoid the error
                created_at = datetime.now().isoformat()
                if st.session_state.config_manager.save_as_template(
                    st.session_state.new_template_name, 
                    st.session_state.template_description,
                    created_at
                ):
                    st.success(f"New template '{st.session_state.new_template_name}' created!")
                    # Reset fields
                    st.session_state.new_template_name = ""
                    st.session_state.template_description = ""
                    # Force rerun to update template list
                    st.rerun()
                else:
                    st.error(f"Failed to create template '{st.session_state.new_template_name}'.")
            else:
                st.error(f"Cannot save invalid configuration: {st.session_state.yaml_error}")
    else:
        # Save to existing template
        if st.button("Save to Template", use_container_width=True):
            # First apply any pending changes from the editor
            if apply_yaml_changes():
                # Pass the current datetime to avoid the error
                created_at = datetime.now().isoformat()
                if st.session_state.config_manager.save_as_template(
                    selected_template, 
                    template_description,
                    created_at
                ):
                    st.success(f"Configuration saved to template '{selected_template}'!")
                else:
                    st.error(f"Failed to save to template '{selected_template}'.")
            else:
                st.error(f"Cannot save invalid configuration: {st.session_state.yaml_error}")

# Get started button
st.markdown("### Ready to get started?")
if st.button("Configure Models", type="primary", use_container_width=True):
    st.switch_page("pages/01_Model_Selection.py")

# Sidebar information
with st.sidebar:
    st.title("About")
    st.markdown(
    """
    **Haystack Multi-LLM Chat** is a tool for comparing responses from different language models.

    Built with:
    - Streamlit
    - Haystack 2.9+
    - AWS Bedrock
    - Ollama

    ---
    ### Requirements

    - Python 3.8+
    - AWS credentials (for Bedrock)
    - Ollama running locally or on accessible server
    """)