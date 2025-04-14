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
import os

# Set page configuration
st.set_page_config(
    page_title="Haystack Multi-LLM Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main content
st.title("🤖 Haystack Multi-LLM Chat")
st.markdown("### Compare responses from multiple language models side-by-side")

# Introduction
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