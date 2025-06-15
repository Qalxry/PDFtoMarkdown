import os
import tempfile
import concurrent.futures
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QComboBox,
    QTabWidget,
    QTextEdit,
    QSpinBox,
    QDoubleSpinBox,
    QMessageBox,
    QProgressBar,
    QGroupBox,
    QRadioButton,
    QCheckBox,
    QFrame,
    QSplitter,
    QInputDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap

from config_manager import ConfigManager
from pdf_processor import PDFProcessor
from openai_client import OpenAIClient
from gui.config_dialog import ConfigDialog
from gui.assistant_manager import AssistantManager
import datetime


class ProcessingTask(QThread):
    progress_updated = pyqtSignal(int, str)
    processing_complete = pyqtSignal(str)

    def __init__(
        self,
        images: List[str],
        openai_client: OpenAIClient,
        system_prompt: str,
        user_prompt: str,
        parallelism: int,
        max_retries: int,
        output_format: str,
    ):
        super().__init__()
        self.images = images
        self.openai_client = openai_client
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.parallelism = parallelism
        self.max_retries = max_retries
        self.output_format = output_format
        self.separator = "\n\n"

    def run(self):
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.parallelism) as executor:
            # Create future for each image
            future_to_image = {
                executor.submit(self.process_image, image_path, idx): (image_path, idx)
                for idx, image_path in enumerate(self.images)
            }

            # Process results as they complete
            for i, future in enumerate(concurrent.futures.as_completed(future_to_image)):
                image_path, idx = future_to_image[future]
                page_num = idx + 1
                try:
                    success, text = future.result()
                    results.append((idx, success, text, page_num))

                    # Report progress
                    progress_percent = int((i + 1) / len(self.images) * 100)
                    self.progress_updated.emit(
                        progress_percent,
                        f"Processed page {page_num}/{len(self.images)}",
                    )
                except Exception as e:
                    results.append((idx, False, str(e), page_num))

        # Sort results by original index
        results.sort(key=lambda x: x[0])

        # Combine all results
        final_text = self.format_results(results)

        # Emit signal with final result
        self.processing_complete.emit(final_text)

    def process_image(self, image_path: str, idx: int) -> tuple:
        """Process a single image with retry logic."""
        page_num = idx + 1
        retries = 0

        while retries <= self.max_retries:
            try:
                # Load image
                image_bytes = PDFProcessor.load_image(image_path)

                # Process with OpenAI
                success, response = self.openai_client.process_image(image_bytes, self.system_prompt, self.user_prompt)

                if success:
                    return True, response

                # If failed, increment retry counter
                retries += 1
                if retries <= self.max_retries:
                    # Wait before retrying (exponential backoff)
                    wait_time = 2**retries
                    self.progress_updated.emit(
                        -1,
                        f"Retrying page {page_num} (attempt {retries}/{self.max_retries})...",
                    )
                    self.msleep(wait_time * 1000)
                else:
                    # Max retries exceeded
                    return False, response

            except Exception as e:
                retries += 1
                if retries <= self.max_retries:
                    # Wait before retrying
                    wait_time = 2**retries
                    self.progress_updated.emit(
                        -1,
                        f"Error on page {page_num}, retrying (attempt {retries}/{self.max_retries})...",
                    )
                    self.msleep(wait_time * 1000)
                else:
                    # Max retries exceeded
                    return False, str(e)

        # Should never reach here, but just in case
        return False, "Maximum retries exceeded"

    def format_results(self, results: List[tuple]) -> str:
        """Format processing results based on output format."""
        output = []

        for _, success, text, page_num in results:
            if success:
                output.append(text)
            else:
                # Format error as markdown quote or plain text
                if self.output_format == "md":
                    error_text = f"> **Error processing page {page_num}:**\n>\n> ```json\n> {text}\n> ```"
                else:
                    error_text = f"--- Error processing page {page_num} ---\n\n{text}\n\n---"
                output.append(error_text)

        # # Join all outputs with separator
        # if self.output_format == "md":
        #     separator = "\n\n---\n\n"
        # else:
        #     separator = "\n\n==========\n\n"

        separator = self.separator

        return separator.join(output)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize configuration
        self.config_manager = ConfigManager()
        openai_config = self.config_manager.get_openai_config()
        self.openai_client = OpenAIClient(openai_config)

        # Set up UI
        self.setup_ui()

        # Initialize state variables
        self.current_file = None
        self.image_paths = []
        self.processing_task = None

        # Load assistant
        self.load_last_assistant()

    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("PDF/Image Analysis with OpenAI")
        self.setMinimumSize(700, 800)

        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # File selection section
        file_group = QGroupBox("Input File")
        file_layout = QHBoxLayout(file_group)

        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_file)

        file_layout.addWidget(self.file_path_label, 1)
        file_layout.addWidget(self.browse_btn)

        # Assistant configuration section
        assistant_group = QGroupBox("Assistant Configuration")
        assistant_layout = QVBoxLayout(assistant_group)

        assistant_top_layout = QHBoxLayout()
        self.assistant_combo = QComboBox()
        self.refresh_assistant_list()
        self.assistant_combo.currentTextChanged.connect(self.load_selected_assistant)

        assistant_btn_layout = QHBoxLayout()
        self.new_assistant_btn = QPushButton("New")
        self.new_assistant_btn.clicked.connect(self.create_new_assistant)
        self.save_assistant_btn = QPushButton("Save")
        self.save_assistant_btn.clicked.connect(self.save_current_assistant)
        self.manage_assistants_btn = QPushButton("Manage")
        self.manage_assistants_btn.clicked.connect(self.manage_assistants)

        assistant_btn_layout.addWidget(self.new_assistant_btn)
        assistant_btn_layout.addWidget(self.save_assistant_btn)
        assistant_btn_layout.addWidget(self.manage_assistants_btn)

        assistant_top_layout.addWidget(QLabel("Assistant:"), 0)
        assistant_top_layout.addWidget(self.assistant_combo, 1)

        # Prompts section
        prompts_layout = QHBoxLayout()

        system_layout = QVBoxLayout()
        self.system_prompt = QTextEdit()
        self.system_prompt.setPlaceholderText("Enter system prompt here...")
        system_layout.addWidget(QLabel("System Prompt:"))
        system_layout.addWidget(self.system_prompt)

        user_layout = QVBoxLayout()
        self.user_prompt = QTextEdit()
        self.user_prompt.setPlaceholderText("Enter user prompt here...")
        user_layout.addWidget(QLabel("User Prompt:"))
        user_layout.addWidget(self.user_prompt)

        prompts_layout.addLayout(system_layout)
        prompts_layout.addLayout(user_layout)

        assistant_layout.addLayout(assistant_top_layout)
        assistant_layout.addLayout(assistant_btn_layout)
        assistant_layout.addLayout(prompts_layout)

        # Processing options section
        options_group = QGroupBox("Processing Options")
        options_layout = QHBoxLayout(options_group)

        # Parallelism settings
        parallelism_layout = QVBoxLayout()
        parallelism_group = QGroupBox("Parallelism")
        parallelism_inner = QHBoxLayout(parallelism_group)

        self.parallelism_spin = QSpinBox()
        self.parallelism_spin.setRange(1, 64)
        self.parallelism_spin.setValue(self.config_manager.get_processing_config().get("parallelism", 3))

        parallelism_inner.addWidget(QLabel("Concurrent tasks:"))
        parallelism_inner.addWidget(self.parallelism_spin)

        # Retry settings
        retry_group = QGroupBox("Retry Options")
        retry_inner = QHBoxLayout(retry_group)

        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 5)
        self.retry_spin.setValue(self.config_manager.get_processing_config().get("max_retries", 3))

        retry_inner.addWidget(QLabel("Max retries:"))
        retry_inner.addWidget(self.retry_spin)

        # Output format
        output_group = QGroupBox("Output Format")
        output_inner = QVBoxLayout(output_group)

        self.md_radio = QRadioButton("Markdown (.md)")
        self.txt_radio = QRadioButton("Plain text (.txt)")

        # Set initial selection based on config
        current_format = self.config_manager.get_output_format()
        if current_format == "md":
            self.md_radio.setChecked(True)
        else:
            self.txt_radio.setChecked(True)

        output_inner.addWidget(self.md_radio)
        output_inner.addWidget(self.txt_radio)

        parallelism_layout.addWidget(parallelism_group)
        parallelism_layout.addWidget(retry_group)

        # Add all option groups to the options layout
        options_layout.addLayout(parallelism_layout)
        options_layout.addWidget(output_group)

        # Add OpenAI config button
        config_btn_layout = QHBoxLayout()
        self.config_openai_btn = QPushButton("Configure OpenAI API Settings")
        self.config_openai_btn.clicked.connect(self.configure_openai)
        config_btn_layout.addStretch()
        config_btn_layout.addWidget(self.config_openai_btn)

        # Process and Output section
        process_layout = QHBoxLayout()
        self.process_btn = QPushButton("Process File")
        self.process_btn.setMinimumHeight(40)
        self.process_btn.clicked.connect(self.process_file)

        self.save_output_btn = QPushButton("Save Output")
        self.save_output_btn.setMinimumHeight(40)
        self.save_output_btn.setEnabled(False)
        self.save_output_btn.clicked.connect(self.save_output)

        process_layout.addWidget(self.process_btn)
        process_layout.addWidget(self.save_output_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_status = QLabel()
        self.progress_status.setVisible(False)

        progress_layout = QVBoxLayout()
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_status)

        # Output text area
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)

        # Add all components to main layout
        main_layout.addWidget(file_group)
        main_layout.addWidget(assistant_group)
        main_layout.addWidget(options_group)
        main_layout.addLayout(config_btn_layout)
        main_layout.addLayout(process_layout)
        main_layout.addLayout(progress_layout)
        main_layout.addWidget(output_group)

        self.setCentralWidget(central_widget)

    def browse_file(self):
        """Open file dialog to select PDF or image."""
        # If a file is already selected, open the dialog in its directory
        initial_dir = ""
        if self.current_file:
            initial_dir = os.path.dirname(self.current_file)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF or Image",
            initial_dir,
            "Files (*.pdf *.jpg *.jpeg *.png)",
        )

        if file_path:
            self.current_file = file_path
            self.file_path_label.setText(os.path.basename(file_path))

    def refresh_assistant_list(self):
        """Refresh the assistant combo box with current assistants."""
        self.assistant_combo.clear()
        assistants = self.config_manager.get_assistants()
        for assistant in assistants:
            self.assistant_combo.addItem(assistant)

    def load_selected_assistant(self, assistant_name: str):
        """Load the selected assistant's prompts."""
        if not assistant_name:
            return

        assistant = self.config_manager.load_assistant(assistant_name)
        if assistant:
            self.system_prompt.setText(assistant.get("system_prompt", ""))
            self.user_prompt.setText(assistant.get("user_prompt", ""))
            self.config_manager.set_last_assistant(assistant_name)
            self.assistant_combo.setCurrentText(assistant_name)

    def load_last_assistant(self):
        """Load the last used assistant."""
        last_assistant = self.config_manager.get_last_assistant()
        if last_assistant and last_assistant in self.config_manager.get_assistants():
            self.assistant_combo.setCurrentText(last_assistant)
            # set the prompts
            self.load_selected_assistant(last_assistant)

    def create_new_assistant(self):
        """Create a new assistant."""
        name, ok = QInputDialog.getText(self, "New Assistant", "Enter assistant name:")

        if ok and name:
            # Check if assistant already exists
            if name in self.config_manager.get_assistants():
                QMessageBox.warning(
                    self,
                    "Assistant Exists",
                    f"An assistant named '{name}' already exists.",
                )
                return

            # Save empty assistant
            self.config_manager.save_assistant(name, "", "")

            # Refresh list and select new assistant
            self.refresh_assistant_list()
            self.assistant_combo.setCurrentText(name)

    def save_current_assistant(self):
        """Save the current assistant."""
        current_name = self.assistant_combo.currentText()
        if not current_name:
            # Prompt for a name if none selected
            self.create_new_assistant()
            return

        # Get current prompts
        system_prompt = self.system_prompt.toPlainText()
        user_prompt = self.user_prompt.toPlainText()

        # Save to configuration
        self.config_manager.save_assistant(current_name, system_prompt, user_prompt)
        self.config_manager.set_last_assistant(current_name)

        QMessageBox.information(self, "Assistant Saved", f"Assistant '{current_name}' has been saved.")

    def manage_assistants(self):
        """Open assistant manager dialog."""
        dialog = AssistantManager(self.config_manager, self)
        if dialog.exec():
            # Refresh list after dialog closes
            self.refresh_assistant_list()
            self.load_last_assistant()

    def configure_openai(self):
        """Open OpenAI configuration dialog."""
        dialog = ConfigDialog(self.config_manager.get_openai_config(), self)
        if dialog.exec():
            # Update config with new values
            new_config = dialog.get_config()
            self.config_manager.update_config(
                {
                    "openai": new_config,
                    "processing": self.config_manager.get_processing_config(),
                    "last_assistant": self.config_manager.get_last_assistant(),
                    "output_format": self.config_manager.get_output_format(),
                }
            )

            # Update OpenAI client
            self.openai_client.update_config(new_config)

    def process_file(self):
        """Process the selected file with OpenAI."""
        if not self.current_file:
            QMessageBox.warning(self, "No File Selected", "Please select a PDF or image file first.")
            return

        # Check if API key is configured
        if not self.openai_client.api_key:
            QMessageBox.warning(
                self,
                "API Key Missing",
                "Please configure your OpenAI API key in settings.",
            )
            return

        # Get prompts
        system_prompt = self.system_prompt.toPlainText()
        user_prompt = self.user_prompt.toPlainText()

        # Allow empty prompts for now
        # if not system_prompt or not user_prompt:
        #     QMessageBox.warning(
        #         self,
        #         "Prompts Missing",
        #         "Please provide both system and user prompts."
        #     )
        #     return

        # Get processing settings
        parallelism = self.parallelism_spin.value()
        max_retries = self.retry_spin.value()

        # Update processing config
        self.config_manager.update_config(
            {
                "openai": self.config_manager.get_openai_config(),
                "processing": {"parallelism": parallelism, "max_retries": max_retries},
                "last_assistant": self.config_manager.get_last_assistant(),
                "output_format": "md" if self.md_radio.isChecked() else "txt",
            }
        )

        # Determine output format
        output_format = "md" if self.md_radio.isChecked() else "txt"
        self.config_manager.set_output_format(output_format)

        # Clear previous output
        self.output_text.clear()

        # Show progress indicators
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_status.setText("Preparing...")
        self.progress_status.setVisible(True)

        # Disable process button
        self.process_btn.setEnabled(False)
        self.save_output_btn.setEnabled(False)

        # Check if input is PDF or image
        file_ext = os.path.splitext(self.current_file)[1].lower()

        if file_ext in [".pptx", ".ppt"]:
            # convert to PDF first
            self.progress_status.setText("Converting PPT to PDF...")
            os.makedirs("./tmp", exist_ok=True)
            
            
        elif file_ext == ".pdf":
            # Convert PDF to images
            self.progress_status.setText("Converting PDF to images...")
            os.makedirs("./tmp", exist_ok=True)
            self.image_paths = PDFProcessor.convert_pdf_to_images(
                self.current_file,
                f"./tmp/{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            )
        else:
            # Single image file
            self.image_paths = [self.current_file]

        # Start processing task
        self.processing_task = ProcessingTask(
            self.image_paths,
            self.openai_client,
            system_prompt,
            user_prompt,
            parallelism,
            max_retries,
            output_format,
        )

        # Connect signals
        self.processing_task.progress_updated.connect(self.update_progress)
        self.processing_task.processing_complete.connect(self.processing_finished)

        # Start the task
        self.processing_task.start()

    def update_progress(self, value: int, message: str):
        """Update progress bar and status message."""
        if value >= 0:
            self.progress_bar.setValue(value)
        self.progress_status.setText(message)

    def processing_finished(self, result_text: str):
        """Process completion callback."""
        # Display result
        self.output_text.setText(result_text)

        # Hide progress bar, update status
        self.progress_bar.setVisible(False)
        self.progress_status.setText("Processing complete!")

        # Re-enable buttons
        self.process_btn.setEnabled(True)
        self.save_output_btn.setEnabled(True)

        # Clean up temporary images (not for single image mode)
        if len(self.image_paths) > 1:
            try:
                # Get directory of first image
                image_dir = os.path.dirname(self.image_paths[0])

                # Check if it's a temporary directory
                if tempfile.gettempdir() in image_dir:
                    for image_path in self.image_paths:
                        if os.path.exists(image_path):
                            os.remove(image_path)

                    # Remove the directory if it's empty
                    if os.path.exists(image_dir) and not os.listdir(image_dir):
                        os.rmdir(image_dir)
            except Exception as e:
                print(f"Error cleaning up temporary files: {e}")

    def save_output(self):
        """Save the output to a file."""
        if not self.output_text.toPlainText():
            return

        # Determine file extension
        ext = "md" if self.md_radio.isChecked() else "txt"

        # Generate default filename from original
        base_name = os.path.basename(self.current_file)
        default_name = os.path.splitext(base_name)[0] + f"_analysis.{ext}"

        # Open save dialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Output", default_name, f"{ext.upper()} Files (*.{ext})")

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.output_text.toPlainText())

                QMessageBox.information(self, "Output Saved", f"Output has been saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error Saving Output",
                    f"An error occurred while saving the output: {str(e)}",
                )
