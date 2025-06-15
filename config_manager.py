import json
import os
from typing import Dict, List, Any, Optional

class ConfigManager:
    def __init__(self):
        self.config_file = "data/config.json"
        self.assistants_dir = "data/assistants"
        self._ensure_dirs_exist()
        self.config = self._load_config()
        
    def _ensure_dirs_exist(self):
        """Ensure all required directories exist."""
        os.makedirs("data", exist_ok=True)
        os.makedirs(self.assistants_dir, exist_ok=True)
        os.makedirs("resources", exist_ok=True)
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from disk or create default."""
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # Default configuration
            default_config = {
                "openai": {
                    "model_id": "gpt-4o",
                    "temperature": 0.7,
                    "top_k": 40,
                    "max_tokens": 1000,
                    "api_url": "https://api.openai.com/v1",
                    "api_key": ""
                },
                "processing": {
                    "parallelism": 3,
                    "max_retries": 3
                },
                "last_assistant": "",
                "output_format": "md"
            }
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to disk."""
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
            
    def update_config(self, config: Dict[str, Any]):
        """Update configuration and save to disk."""
        self.config = config
        self._save_config(config)
        
    def get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI configuration."""
        return self.config.get("openai", {})
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration."""
        return self.config.get("processing", {})
    
    def get_assistants(self) -> List[str]:
        """Get list of available assistants."""
        return [f.replace(".json", "") for f in os.listdir(self.assistants_dir) 
                if f.endswith(".json")]
    
    def save_assistant(self, name: str, system_prompt: str, user_prompt: str):
        """Save assistant configuration."""
        assistant = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }
        with open(f"{self.assistants_dir}/{name}.json", "w", encoding="utf-8") as f:
            json.dump(assistant, f, indent=2, ensure_ascii=False)
            
    def load_assistant(self, name: str) -> Optional[Dict[str, str]]:
        """Load assistant configuration."""
        path = f"{self.assistants_dir}/{name}.json"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def delete_assistant(self, name: str) -> bool:
        """Delete assistant configuration."""
        path = f"{self.assistants_dir}/{name}.json"
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
    
    def set_last_assistant(self, name: str):
        """Set last used assistant."""
        self.config["last_assistant"] = name
        self._save_config(self.config)
        
    def get_last_assistant(self) -> str:
        """Get last used assistant."""
        return self.config.get("last_assistant", "")
    
    def set_output_format(self, format_type: str):
        """Set output format (md or txt)."""
        self.config["output_format"] = format_type
        self._save_config(self.config)
        
    def get_output_format(self) -> str:
        """Get output format."""
        return self.config.get("output_format", "md")