# Haystack Multi-LLM Chat: Architecture and Design Document

## 1. System Architecture Overview

### 1.1 High-Level Architecture

The Haystack Multi-LLM Chat application is a Streamlit-based web application that allows users to interact with multiple Large Language Models (LLMs) simultaneously. The application integrates with Haystack 2.12+ to provide a unified interface for different LLM providers. This is currently in a proof-of-concept state with major changes planned.

```
┌─────────────────┐     ┌───────────────┐     ┌─────────────────────┐
│                 │     │               │     │                     │
│  Streamlit UI   │◄────┤  Haystack     │◄────┤  LLM Providers      │
│  - Multi-page   │     │  Components   │     │  - AWS Bedrock      │
│  - Session      │─────┤               │─────┤  - Ollama           │
│    Management   │     │               │     │  - (Extensible)     │
│                 │     │               │     │                     │
└─────────────────┘     └───────────────┘     └─────────────────────┘
```

### 1.2 Data Flow

#### 1.2.1 Model Selection Flow

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│            │     │            │     │            │     │            │
│  Provider  │────►│  Model     │────►│ Parameter  │────►│  Save to   │
│  Selection │     │  Discovery │     │ Config     │     │  Session   │
│            │     │            │     │            │     │            │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
```

#### 1.2.2 Chat Flow

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│            │     │            │     │            │     │            │
│  User      │────►│ Process    │────►│ Generate   │────►│  Display   │
│  Input     │     │ History    │     │ Responses  │     │  Responses │
│            │     │            │     │            │     │            │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
                                          │
                                          ▼
                                     ┌────────────┐     ┌────────────┐
                                     │            │     │            │
                                     │  Response  │────►│  Update    │
                                     │  Selection │     │  History   │
                                     │            │     │            │
                                     └────────────┘     └────────────┘
```

#### 1.2.3 Document Integration Flow

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│            │     │            │     │            │     │            │
│  Browse    │────►│  Select    │────►│  Format    │────►│  Include   │
│  Files     │     │  Documents │     │  Documents │     │  in Chat   │
│            │     │            │     │            │     │            │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
```

## 2. Component Documentation

### 2.1 Page Structure

#### 2.1.1 Main Page (`app.py`)
- **Purpose**: Application landing page and configuration management
- **Functionality**:
  - Displays application overview
  - Provides navigation to model configuration
  - Shows requirements and information about supported providers
  - Manages application configuration through ConfigManager
  - Provides YAML editor for direct configuration editing
  - Supports template management for configuration templates
- **Key Components**:
  - Introduction section
  - Configuration management interface
  - Template management interface
  - "Configure Models" button to start workflow

#### 2.1.2 Model Selection (`01_Model_Selection.py`)
- **Purpose**: Configure and select LLM models
- **Functionality**:
  - Discover available models from providers
  - Configure model parameters
  - Set system prompt for all models
  - Manage list of selected models
- **Key Components**:
  - Provider selection interface (now using ConfigManager)
  - Model discovery functions (`get_ollama_models()`, `get_bedrock_models()`)
  - Parameter configuration UI
  - Selected models display and management
  - System prompt configuration (now stored in ConfigManager)

#### 2.1.3 Document Selection (`02_Documents.py`)
- **Purpose**: Select and format documents for context
- **Functionality**:
  - Browse local file system
  - Select documents to include in conversation
  - Configure document formatting options
  - Set instructions for document handling
- **Key Components**:
  - File browser with recursive option (config from ConfigManager)
  - Document selection interface
  - Format selection (XML, Markdown, Simple)
  - Document instructions configuration
  - Preview functionality

#### 2.1.4 Chat Interface (`03_Chat.py`)
- **Purpose**: Main conversation interface
- **Functionality**:
  - Display conversation history
  - Send user messages to selected models
  - Show side-by-side model responses
  - Allow selection of preferred responses
  - Support slash commands
- **Key Components**:
  - Chat history display
  - LLM generator initialization
  - Response streaming implementation
  - Side-by-side response UI
  - Response selection mechanism

#### 2.1.5 Saved Chats (`04_Saved_Chats.py`)
- **Purpose**: Manage saved conversations
- **Functionality**:
  - Save current chat session
  - Browse saved chats
  - Preview chat contents
  - Load saved chat into active session
  - Delete saved chats
- **Key Components**:
  - Chat serialization/deserialization
  - File management interface
  - Chat preview display
  - Session restoration logic

#### 2.1.6 Search Interface (`05_Search.py`)
- **Purpose**: Search through document content and add relevant snippets to chat
- **Functionality**:
  - Index markdown files from specified directories
  - Execute keyword searches across indexed content
  - Select specific snippets or entire documents from search results
  - Format and include selected content in conversation
- **Key Components**:
  - Document indexing with BM25 retriever
  - Document chunking for large files
  - Search interface with result highlighting
  - Selection management for snippets and full documents
  - Preview of formatted content

### 2.2 Configuration Management

The application uses a centralized ConfigManager to handle all configuration:

#### 2.2.1 ConfigManager

The `ConfigManager` class provides a centralized way to manage application configuration with the following features:

- **Hierarchical Configuration**: Organized into global, page-specific, and provider-specific settings
- **Configuration Persistence**: Save/load configuration to/from YAML files
- **Template Support**: Save and load configuration templates
- **Fallback Mechanism**: Page settings can fall back to global defaults

#### 2.2.2 Configuration Structure

```yaml
global:
  # Settings used across multiple pages
  base_directories:
    documents: "./data/documents"
    saved_chats: "./saved_chats"
  system_prompt: "You are a helpful AI assistant."
  ignored_directories: [".git", ".env"]
pages:
  # Page-specific settings
  model_selection:
    default_provider: "bedrock"
  documents:
    recursive: true
    format: "xml"
providers:
  # Provider-specific settings
  bedrock:
    region: "us-east-1"
  # Other provider settings...
```

#### 2.2.3 Session State Management

The application still uses Streamlit session state to maintain application state across page navigation and reruns:

| Session State Variable    | Description                         | Initialized In  | Used In           |
|---------------------------|-------------------------------------|-----------------|-------------------|
| `config_manager`          | ConfigManager instance              | app.py          | All pages         |
| `selected_models`         | List of configured models           | Model Selection | All pages         |
| `messages`                | Conversation history                | Chat            | Chat, Saved Chats |
| `last_user_msg_idx`       | Index of last user message          | Chat            | Chat              |
| `awaiting_selection`      | Flag for pending response selection | Chat            | Chat              |
| `selected_documents`      | List of selected document data      | Documents       | Documents, Chat   |
| `streaming_[model_id]`    | Buffer for streaming responses      | Chat            | Chat              |
| `placeholder_[model_id]`  | UI placeholder for streaming        | Chat            | Chat              |
| `search_document_store`   | In-memory document store for search | Search          | Search            |
| `search_retriever`        | BM25 retriever for document search  | Search          | Search            |
| `indexed_files`           | Set of files that have been indexed | Search          | Search            |
| `selected_search_results` | List of selected search results     | Search          | Search, Chat      |
| `last_search_results`     | Results from most recent search     | Search          | Search            |
| `last_search_query`       | Most recent search query            | Search          | Search            |

### 2.3 External API Integration

#### 2.3.1 AWS Bedrock
- **Integration Component**: `AmazonBedrockChatGenerator`
- **Authentication**: AWS credentials from environment
- **Model Discovery**: `boto3.client('bedrock').list_foundation_models()`
- **Request Flow**:
  1. Initialize generator with model name and parameters
  2. Convert messages to format expected by Bedrock
  3. Send request with streaming enabled
  4. Process streaming chunks in callback

#### 2.3.2 Ollama
- **Integration Component**: `OllamaChatGenerator`
- **Authentication**: None (direct API access)
- **Model Discovery**: `GET /api/tags` endpoint
- **Request Flow**:
  1. Initialize generator with model name, URL, and parameters
  2. Convert messages to format expected by Ollama
  3. Send request with streaming enabled
  4. Process streaming chunks in callback

#### 2.3.3 Haystack Document Store and Retriever
- **Integration Component**: `InMemoryDocumentStore` and `InMemoryBM25Retriever`
- **Authentication**: None (in-memory components)
- **Document Processing**: Chunking large documents into manageable segments
- **Request Flow**:
  1. Index documents into document store
  2. Create retriever connected to document store
  3. Execute search queries through retriever
  4. Process and display search results

## 3. Design Patterns and Decisions

### 3.1 Configuration Management Pattern

The application uses the ConfigManager to centralize all configuration handling:

1. **Hierarchical Configuration**:
   - Global settings apply across the entire application
   - Page-specific settings override global defaults
   - Provider-specific settings for individual LLM providers

2. **Configuration Access Pattern**:
   ```python
   # Get the ConfigManager instance
   config = st.session_state.config_manager
   
   # Access global configuration
   system_prompt = config.get_global("system_prompt", "Default prompt")
   
   # Access page-specific configuration
   recursive = config.get_page_config("documents", "recursive", False)
   
   # Access provider-specific configuration
   region = config.get_provider_config("bedrock", "region", "us-east-1")
   
   # Access with fallback to global
   format = config.get_page_config_with_fallback(
       "documents", "format", "documents", "format", "xml"
   )
   ```

3. **Configuration Persistence**:
   - Configuration is loaded from `config/app_config.yaml` at startup
   - Changes can be saved back to the file for persistence
   - Template system allows saving/loading different configurations

### 3.2 Conversation History Management

The application uses a hybrid approach to conversation history:

1. **Complete History Storage**:
   - All messages (user and assistant) are stored in `st.session_state.messages`
   - Each message is a `ChatMessage` object with role, content, and metadata

2. **Filtered History for LLMs**:
   - Only user messages and *selected* assistant responses are sent to LLMs
   - This ensures all models see the same conversation context
   - Implemented in `get_user_and_selected_responses()` function

3. **Message Grouping**:
   - User messages and their corresponding model responses are grouped
   - The `last_user_msg_idx` tracks the position of the last user message
   - Responses are displayed side-by-side using this grouping

### 3.3 Streaming Response Handling

The application implements streaming responses through:

1. **Streaming Callback Pattern**:
   - Each model generator is initialized with a streaming callback function
   - The callback appends content to a model-specific buffer in session state
   - The buffer is rendered in real-time to a placeholder element

2. **Model-Specific UI Elements**:
   - Each model has its own placeholder for streaming content
   - Placeholders are stored in session state with model-specific keys
   - This enables parallel streaming from multiple models

3. **Streaming Buffer Management**:
   - Buffers are initialized at the start of each generation
   - Content is accumulated in the buffer during streaming
   - Final content is stored in the message history after completion

### 3.4 Side-by-Side Comparison Implementation

The side-by-side comparison is implemented through:

1. **Dynamic Column Creation**:
   - Streamlit columns are created based on the number of responses
   - Each column displays one model's response

2. **Response Selection Mechanism**:
   - Radio buttons in each column allow selecting preferred responses
   - Selection state is stored in message metadata (`meta["selected"]`)
   - Only one response can be selected per user message

3. **Selection Enforcement**:
   - The `awaiting_selection` flag blocks new input until selection is made
   - This ensures the conversation history is consistent for all models
   - Selection is only required when multiple models are used

### 3.5 Document Context Integration

Documents are integrated into the conversation through:

1. **First Message Augmentation**:
   - Documents are prepended to the first user message only
   - This avoids repeating document context in every message

2. **Format Templating**:
   - Documents are formatted according to the selected style (XML, Markdown, Simple)
   - Each format has a specific template for document name and content
   - Format settings are stored in ConfigManager

3. **Instruction Prefixing**:
   - Custom instructions are added before document content
   - This guides the model on how to use the documents
   - Instructions are stored in ConfigManager

4. **Document Search and Selection**:
   - Documents can be browsed directly or discovered through search
   - Search allows finding specific content within large document collections
   - Both snippets and full documents can be selected from search results

### 3.6 Search Implementation

The document search functionality is implemented through:

1. **Document Indexing**:
   - Markdown files are indexed using Haystack's document store
   - Large documents are automatically chunked into smaller segments
   - Both snippets and full documents are stored for retrieval

2. **BM25 Retrieval**:
   - Keyword search uses the BM25 algorithm for relevance ranking
   - Results are filtered to show document snippets by default

3. **Result Selection Mechanism**:
   - Users can add specific snippets or entire documents to their selection
   - Selected items are formatted according to user preferences
   - Selected content is included in the first message to the model

## 4. Directory structure
Haystack-MultiLLM-Chat/
├── .github/                      # GitHub-specific files
│   └── workflows/                # GitHub Actions workflows (CI/CD)
├── src/                          # Source code directory
│   ├── app.py                    # Main entry point for the app
│   ├── pages/                    # Streamlit pages
│   │   ├── 01_Model_Selection.py # Select AI models
│   │   ├── 02_Documents.py       # Document selection
│   │   ├── 03_Chat.py            # AI chat
│   │   ├── 04_Saved_Chats.py     # Save and load chats
│   │   └── 05_Search.py          # Document search functionality
│   ├── utils/                    # Utility functions
│   │   └── config_manager.py     # Configuration management
│   ├── components/               # Reusable UI components
│   ├── providers/                # Provider-specific implementations
│   └── config/                   # Configuration files
│       └── app_config.yaml       # Default application configuration
├── tests/                        # Test directory
├── docs/                         # Documentation
├── data/                         # Sample data and saved chats
├── .gitignore                    # Git ignore file
├── requirements.txt              # Python dependencies
├── LICENSE                       # License file
└── README.md                     # Project README

## 5. Extension Guide

### 5.1 Adding New LLM Providers

To add a new LLM provider:

1. **Update Model Selection Page**:
   - Add the provider to the `provider_options` list
   - Create a provider-specific configuration section in the if-else chain
   - Implement a model discovery function (similar to `get_bedrock_models()`)

2. **Create Generator Integration**:
   - Import or implement a Haystack generator for the provider
   - Add a case in the `get_generator()` function to initialize the generator
   - Implement streaming callback for the provider

3. **Update Provider Configuration**:
   - Add provider-specific settings to the ConfigManager
   - Update the default configuration in `app_config.yaml`

### 5.2 Implementing New Features

#### 5.2.1 Adding Configuration Options

To add new configuration options:

1. **Update ConfigManager**:
   - Determine whether the setting belongs in global, page, or provider section
   - Add the setting to the default configuration in `app_config.yaml`

2. **Access in Code**:
   ```python
   # For global settings
   setting = config.get_global("setting_name", default_value)
   
   # For page settings
   setting = config.get_page_config("page_name", "setting_name", default_value)
   
   # For provider settings
   setting = config.get_provider_config("provider_name", "setting_name", default_value)
   ```

#### 5.2.2 Adding Document Processing Capabilities

Todo: add document chunking and embedding:

### 5.3 Best Practices for Maintenance

#### 5.3.1 Code Organization

- **Modularize Common Functions**: Extract shared functionality into separate Python modules
- **Consistent Naming**: Use consistent naming conventions for variables and functions
- **Configuration Management**: Use ConfigManager for all settings, avoid direct session state
- **Session State Management**: Use session state only for application state, not configuration

#### 5.3.2 Error Handling

- **Graceful Degradation**: Handle API failures without crashing the application
- **User Feedback**: Provide clear error messages to users
- **Retry Logic**: Implement exponential backoff for rate-limited API calls

#### 5.3.3 Performance Optimization

- **Caching**: Use `@st.cache_data` and `@st.cache_resource` appropriately
- **Lazy Loading**: Only load resources when needed
- **Pagination**: Implement pagination for large lists of models or documents

#### 5.3.4 Testing

- **Unit Tests**: Write tests for core functionality
- **Integration Tests**: Test integration with each LLM provider
- **UI Testing**: Verify UI components behave correctly

## 6. Known Issues and Solutions

### 6.1 AWS Bedrock Throttling

**Issue**: The application encounters `ThrottlingException` when calling the `ConverseStream` operation.

**Workaround**: An error message instructs the user to wait, then use the `/retry` command.

**Solution**:
1. Implement exponential backoff and retry logic:
2. Add rate limiting to prevent throttling:

### 6.2 Large Document Handling

**Issue**: Large documents may exceed model context windows.

## 7. Future Enhancements

### 7.1 Additional LLM Providers

### 7.2 Advanced Features

- **Chat History Analytics**: Statistics and insights from conversation history
- **Document Retrieval**: RAG (Retrieval-Augmented Generation) capabilities
- **Fine-tuning Interface**: UI for fine-tuning models based on conversations

### 7.3 UI/UX Improvements

- **Responsive Design**: Better mobile support
- **Dark Mode**: Toggle between light and dark themes
- **Customizable Layout**: Allow users to resize and rearrange panels
- **Keyboard Shortcuts**: Add keyboard shortcuts for common actions

## 8. Conclusion

The Haystack Multi-LLM Chat application provides a flexible framework for interacting with multiple LLMs simultaneously. Its modular design allows for easy extension with new providers and features. By following the patterns and practices outlined in this document, developers can maintain and enhance the application while preserving its core functionality and user experience.

## License

Haystack Multi-LLM Chat
Copyright (C) 2025 DigitalReplica

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
