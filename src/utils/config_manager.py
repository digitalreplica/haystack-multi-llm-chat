import yaml
import os
import streamlit as st
from typing import Any, Dict, Optional, Union, List

class ConfigManager:
    """
    Manages application configuration, including loading/saving configuration files,
    accessing configuration values with proper override precedence, and managing templates.
    """

    def __init__(self, app_config_path: str = "config/app_config.yaml", 
                 templates_dir: str = "config/templates"):
        """Initialize the configuration manager"""
        self.app_config_path = app_config_path
        self.templates_dir = templates_dir

        # Ensure configuration directories exist
        os.makedirs(os.path.dirname(app_config_path), exist_ok=True)
        os.makedirs(templates_dir, exist_ok=True)

        # Initialize configuration structure if not already in session state
        if "config" not in st.session_state:
            # Load application config or create default
            if os.path.exists(app_config_path):
                self.load_app_config()
            else:
                self._initialize_default_config()

    def _initialize_default_config(self):
        """Create a default configuration structure"""
        st.session_state.config = {
            "global": {
                "base_directories": {
                    "documents": "./data/documents",
                    "saved_chats": "./saved_chats"
                },
                "system_prompt": "You are a helpful AI assistant.",
                "ignored_directories": [".git", ".env"]
            },
            "pages": {},
            "providers": {}
        }
        # Save the default configuration
        self.save_app_config()

    def load_app_config(self) -> bool:
        """Load the application configuration from file"""
        try:
            with open(self.app_config_path, 'r') as file:
                st.session_state.config = yaml.safe_load(file) or {}
                if "global" not in st.session_state.config:
                    st.session_state.config["global"] = {}
                if "pages" not in st.session_state.config:
                    st.session_state.config["pages"] = {}
                if "providers" not in st.session_state.config:
                    st.session_state.config["providers"] = {}
                return True
        except Exception as e:
            st.error(f"Error loading application configuration: {str(e)}")
            self._initialize_default_config()
            return False

    def save_app_config(self) -> bool:
        """Save the current configuration as the application config"""
        try:
            with open(self.app_config_path, 'w') as file:
                yaml.dump(st.session_state.config, file, sort_keys=False, default_flow_style=False)
            return True
        except Exception as e:
            st.error(f"Error saving application configuration: {str(e)}")
            return False

    def load_template(self, template_name: str) -> bool:
        """Load a configuration template"""
        template_path = os.path.join(self.templates_dir, f"{template_name}.yaml")
        try:
            with open(template_path, 'r') as file:
                template_config = yaml.safe_load(file) or {}

                # Apply template over current configuration
                # (deep merge would be implemented here)
                self._merge_config(st.session_state.config, template_config)

                # Store the active template name
                st.session_state.active_template = template_name
                return True
        except Exception as e:
            st.error(f"Error loading template '{template_name}': {str(e)}")
            return False

    def save_as_template(self, template_name: str, description: str = "") -> bool:
        """Save current configuration as a template"""
        template_path = os.path.join(self.templates_dir, f"{template_name}.yaml")

        # Add metadata to the template
        template_config = dict(st.session_state.config)
        template_config["_metadata"] = {
            "template_name": template_name,
            "description": description,
            "created_at": datetime.now().isoformat()
        }

        try:
            with open(template_path, 'w') as file:
                yaml.dump(template_config, file, sort_keys=False, default_flow_style=False)
            return True
        except Exception as e:
            st.error(f"Error saving template '{template_name}': {str(e)}")
            return False

    def list_templates(self) -> List[Dict[str, Any]]:
        """Get list of available templates with metadata"""
        templates = []
        if os.path.exists(self.templates_dir):
            for file_name in os.listdir(self.templates_dir):
                if file_name.endswith(".yaml"):
                    template_name = file_name[:-5]  # Remove .yaml extension
                    template_path = os.path.join(self.templates_dir, file_name)

                    # Try to load metadata
                    metadata = {"template_name": template_name}
                    try:
                        with open(template_path, 'r') as file:
                            config = yaml.safe_load(file) or {}
                            if "_metadata" in config:
                                metadata.update(config["_metadata"])
                    except:
                        pass

                    templates.append(metadata)
        return templates

    def get_global(self, key: str, default: Any = None) -> Any:
        """Get a global configuration value"""
        if "config" not in st.session_state:
            return default
        return st.session_state.config.get("global", {}).get(key, default)

    def set_global(self, key: str, value: Any) -> None:
        """Set a global configuration value"""
        if "config" not in st.session_state:
            st.session_state.config = {"global": {}, "pages": {}, "providers": {}}
        st.session_state.config["global"][key] = value

    def get_page_config(self, page_name: str, key: str, default: Any = None) -> Any:
        """Get a page-specific configuration value"""
        if "config" not in st.session_state:
            return default
        return st.session_state.config.get("pages", {}).get(page_name, {}).get(key, default)

    def set_page_config(self, page_name: str, key: str, value: Any) -> None:
        """Set a page-specific configuration value"""
        if "config" not in st.session_state:
            st.session_state.config = {"global": {}, "pages": {}, "providers": {}}
        if page_name not in st.session_state.config.get("pages", {}):
            st.session_state.config["pages"][page_name] = {}
        st.session_state.config["pages"][page_name][key] = value

    def get_provider_config(self, provider_name: str, key: str, default: Any = None) -> Any:
        """Get a provider-specific configuration value"""
        if "config" not in st.session_state:
            return default
        return st.session_state.config.get("providers", {}).get(provider_name, {}).get(key, default)

    def set_provider_config(self, provider_name: str, key: str, value: Any) -> None:
        """Set a provider-specific configuration value"""
        if "config" not in st.session_state:
            st.session_state.config = {"global": {}, "pages": {}, "providers": {}}
        if provider_name not in st.session_state.config.get("providers", {}):
            st.session_state.config["providers"][provider_name] = {}
        st.session_state.config["providers"][provider_name][key] = value

    def _merge_config(self, base_config: Dict[str, Any], overlay_config: Dict[str, Any]) -> None:
        """
        Deep merge overlay_config into base_config
        This modifies base_config in place to contain values from overlay_config
        """
        for key, value in overlay_config.items():
            # Skip metadata
            if key == "_metadata":
                continue

            if isinstance(value, dict) and key in base_config and isinstance(base_config[key], dict):
                # Recursively merge dictionaries
                self._merge_config(base_config[key], value)
            else:
                # Replace or add value
                base_config[key] = value