from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QMessageBox, QInputDialog, QLabel
)
from config_manager import ConfigManager

class AssistantManager(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Manage Assistants")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Assistant Configurations")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # Assistant List
        self.assistant_list = QListWidget()
        self.populate_assistant_list()
        layout.addWidget(self.assistant_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.rename_btn = QPushButton("Rename")
        self.rename_btn.clicked.connect(self.rename_assistant)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_assistant)
        
        self.clone_btn = QPushButton("Clone")
        self.clone_btn.clicked.connect(self.clone_assistant)
        
        button_layout.addWidget(self.rename_btn)
        button_layout.addWidget(self.clone_btn)
        button_layout.addWidget(self.delete_btn)
        
        # Close button
        close_layout = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_layout.addStretch()
        close_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        layout.addLayout(close_layout)
        
    def populate_assistant_list(self):
        """Fill the list with available assistants."""
        self.assistant_list.clear()
        assistants = self.config_manager.get_assistants()
        for assistant in assistants:
            self.assistant_list.addItem(assistant)
            
    def rename_assistant(self):
        """Rename the selected assistant."""
        current_item = self.assistant_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, 
                "No Assistant Selected", 
                "Please select an assistant to rename."
            )
            return
            
        current_name = current_item.text()
        new_name, ok = QInputDialog.getText(
            self, 
            "Rename Assistant", 
            "New name:", 
            text=current_name
        )
        
        if ok and new_name and new_name != current_name:
            # Check if name already exists
            if new_name in self.config_manager.get_assistants():
                QMessageBox.warning(
                    self, 
                    "Name Exists", 
                    f"An assistant named '{new_name}' already exists."
                )
                return
                
            # Get assistant data
            assistant = self.config_manager.load_assistant(current_name)
            if assistant:
                # Save with new name
                self.config_manager.save_assistant(
                    new_name, 
                    assistant.get("system_prompt", ""), 
                    assistant.get("user_prompt", "")
                )
                
                # Delete old assistant
                self.config_manager.delete_assistant(current_name)
                
                # Update last assistant if needed
                if self.config_manager.get_last_assistant() == current_name:
                    self.config_manager.set_last_assistant(new_name)
                    
                # Refresh list
                self.populate_assistant_list()
                
    def delete_assistant(self):
        """Delete the selected assistant."""
        current_item = self.assistant_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, 
                "No Assistant Selected", 
                "Please select an assistant to delete."
            )
            return
            
        assistant_name = current_item.text()
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            "Confirm Deletion", 
            f"Are you sure you want to delete assistant '{assistant_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Delete the assistant
            self.config_manager.delete_assistant(assistant_name)
            
            # If this was the last assistant, clear it
            if self.config_manager.get_last_assistant() == assistant_name:
                self.config_manager.set_last_assistant("")
                
            # Refresh list
            self.populate_assistant_list()
            
    def clone_assistant(self):
        """Clone the selected assistant."""
        current_item = self.assistant_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, 
                "No Assistant Selected", 
                "Please select an assistant to clone."
            )
            return
            
        source_name = current_item.text()
        new_name, ok = QInputDialog.getText(
            self, 
            "Clone Assistant", 
            "New assistant name:", 
            text=f"{source_name} - Copy"
        )
        
        if ok and new_name:
            # Check if name already exists
            if new_name in self.config_manager.get_assistants():
                QMessageBox.warning(
                    self, 
                    "Name Exists", 
                    f"An assistant named '{new_name}' already exists."
                )
                return
                
            # Get source assistant data
            assistant = self.config_manager.load_assistant(source_name)
            if assistant:
                # Save with new name
                self.config_manager.save_assistant(
                    new_name, 
                    assistant.get("system_prompt", ""), 
                    assistant.get("user_prompt", "")
                )
                
                # Refresh list
                self.populate_assistant_list()