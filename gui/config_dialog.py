from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QPushButton,
    QDialogButtonBox,
    QFormLayout,
    QCheckBox,
    QGroupBox,
)
from typing import Dict, Any


class ConfigDialog(QDialog):
    def __init__(self, config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("OpenAI API Configuration")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        # API Access Group
        api_group = QGroupBox("API Access")
        api_layout = QFormLayout(api_group)

        # API Key
        self.api_key_input = QLineEdit(self.config.get("api_key", ""))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        show_key_btn = QPushButton("Show")

        key_layout = QHBoxLayout()
        key_layout.addWidget(self.api_key_input)
        key_layout.addWidget(show_key_btn)
        show_key_btn.clicked.connect(self.toggle_api_key_visibility)

        # API URL
        self.api_url_input = QLineEdit(
            self.config.get("api_url", "https://api.openai.com/v1")
        )
        self.api_url_input.setPlaceholderText("https://api.openai.com/v1")

        api_layout.addRow("API Key:", key_layout)
        api_layout.addRow("API URL:", self.api_url_input)

        # Model Configuration Group
        model_group = QGroupBox("Model Configuration")
        model_layout = QFormLayout(model_group)

        # Model ID text input
        self.model_id_input = QLineEdit(self.config.get("model_id", "gpt-4o"))

        # Temperature
        self.temperature_input = QDoubleSpinBox()
        self.temperature_input.setRange(0.0, 2.0)
        self.temperature_input.setSingleStep(0.1)
        self.temperature_input.setValue(self.config.get("temperature", 0.7))

        # Top K
        self.top_k_input = QSpinBox()
        self.top_k_input.setRange(1, 100)
        self.top_k_input.setValue(self.config.get("top_k", 100))

        # Max Tokens
        self.max_tokens_input = QSpinBox()
        self.max_tokens_input.setRange(0, 10000000)
        self.max_tokens_input.setSingleStep(100)
        self.max_tokens_input.setValue(self.config.get("max_tokens", 0))

        # Streaming
        self.stream_checkbox = QCheckBox()
        self.stream_checkbox.setChecked(self.config.get("stream", True))
        self.stream_checkbox.setToolTip("Enable streaming for faster responses.")

        # Repair Formula Tag
        self.repair_formula_tag_checkbox = QCheckBox()
        self.repair_formula_tag_checkbox.setChecked(
            self.config.get("repair_formula_tag", True)
        )
        self.repair_formula_tag_checkbox.setToolTip(
            "Enable repair formula tag for better formatting."
        )

        model_layout.addRow("Model:", self.model_id_input)
        model_layout.addRow("Temperature:", self.temperature_input)
        model_layout.addRow("Top K:", self.top_k_input)
        model_layout.addRow("Max Tokens:", self.max_tokens_input)
        model_layout.addRow("Streaming:", self.stream_checkbox)
        model_layout.addRow("Repair Formula Tag:", self.repair_formula_tag_checkbox)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # Add all to main layout
        layout.addWidget(api_group)
        layout.addWidget(model_group)
        layout.addWidget(buttons)

    def toggle_api_key_visibility(self):
        """Toggle the visibility of the API key."""
        if self.api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.sender().setText("Hide")
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.sender().setText("Show")

    def get_config(self) -> Dict[str, Any]:
        """Return the current configuration."""
        return {
            "api_key": self.api_key_input.text().strip(),
            "api_url": self.api_url_input.text().strip() or "https://api.openai.com/v1",
            "model_id": self.model_id_input.text().strip(),
            "temperature": self.temperature_input.value(),
            "top_k": self.top_k_input.value(),
            "max_tokens": self.max_tokens_input.value(),
            "stream": self.stream_checkbox.isChecked(),
            "repair_formula_tag": self.repair_formula_tag_checkbox.isChecked(),
        }
