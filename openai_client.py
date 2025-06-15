from typing import Dict, Any, Optional, Tuple
import base64
import json
from openai import OpenAI


class OpenAIClient:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.setup_client()

    def setup_client(self):
        """Configure the client with current settings."""
        self.model_id = self.config.get("model_id", "gpt-4o")
        self.temperature = self.config.get("temperature", 0.7)
        self.max_tokens = self.config.get("max_tokens", 0)
        self.top_k = self.config.get("top_k", 100)
        self.api_key = self.config.get("api_key", "")
        self.api_url = self.config.get("api_url", "https://api.openai.com/v1")
        self.stream = self.config.get("stream", True)
        self.repair_formula_tag = self.config.get("repair_formula_tag", True)
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_url)

    def update_config(self, config: Dict[str, Any]):
        """Update client configuration."""
        self.config = config
        self.setup_client()

    def process_image(
        self, image_bytes: bytes, system_prompt: str, user_prompt: str
    ) -> Tuple[bool, str]:
        """
        Send image with prompts to OpenAI API using the openai package.
        Embeds the image (base64 encoded) in markdown format.
        Returns tuple of (success, response_text)
        """
        # Encode image as base64 and embed in markdown image syntax.
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": system_prompt},
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                    },
                    {"type": "text", "text": user_prompt},
                ],
            },
        ]

        params = {
            "model": self.model_id,
            "messages": messages,
            "temperature": self.temperature,
            # "top_k": self.top_k,
            "stream": self.stream,
        }
        if self.max_tokens > 0:
            params["max_tokens"] = self.max_tokens

        if "stream" in params and params["stream"]:
            try:
                completion = self.client.chat.completions.create(**params)
                message_content = ""
                for chunk in completion:
                    if chunk.choices[0].delta.content is None:
                        continue
                    message_content += chunk.choices[0].delta.content
                #     print(chunk.choices[0].delta.content, end="")
                # print()
                if self.repair_formula_tag:
                    message_content = (
                        message_content.replace("\\(", "$")
                        .replace("\\)", "$")
                        .replace("\\[", "$$")
                        .replace("\\]", "$$")
                    )
                return True, message_content
            except Exception as e:
                return False, str(e)
        else:
            try:
                completion = self.client.chat.completions.create(**params)
                message_content = completion.choices[0].message.content
                # print(message_content)
                if self.repair_formula_tag:
                    message_content = (
                        message_content.replace("\\(", "$")
                        .replace("\\)", "$")
                        .replace("\\[", "$$")
                        .replace("\\]", "$$")
                    )
                return True, message_content
            except Exception as e:
                return False, str(e)
