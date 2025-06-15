import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Load stylesheet
    with open("resources/styles.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()