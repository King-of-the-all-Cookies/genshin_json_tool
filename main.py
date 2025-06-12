import os
import json
import shutil
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt

class VoiceExtractorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Genshin Voice Extractor")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        json_layout = QHBoxLayout()
        json_layout.addWidget(QLabel("JSON File:"))
        self.json_path_edit = QLineEdit()
        self.json_path_edit.setReadOnly(True)
        json_layout.addWidget(self.json_path_edit)
        self.json_browse_btn = QPushButton("Browse")
        self.json_browse_btn.clicked.connect(self.browse_json)
        json_layout.addWidget(self.json_browse_btn)
        main_layout.addLayout(json_layout)

        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Source WEM Folder:"))
        self.source_folder_edit = QLineEdit()
        self.source_folder_edit.setReadOnly(True)
        source_layout.addWidget(self.source_folder_edit)
        self.source_browse_btn = QPushButton("Browse")
        self.source_browse_btn.clicked.connect(self.browse_source_folder)
        source_layout.addWidget(self.source_browse_btn)
        main_layout.addLayout(source_layout)

        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Folder:"))
        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setReadOnly(True)
        output_layout.addWidget(self.output_folder_edit)
        self.output_browse_btn = QPushButton("Browse")
        self.output_browse_btn.clicked.connect(self.browse_output_folder)
        output_layout.addWidget(self.output_browse_btn)
        main_layout.addLayout(output_layout)

        char_layout = QHBoxLayout()
        char_layout.addWidget(QLabel("Character Filter:"))
        self.char_filter_edit = QLineEdit()
        self.char_filter_edit.setPlaceholderText("Leave empty for all characters")
        char_layout.addWidget(self.char_filter_edit)
        main_layout.addLayout(char_layout)

        quest_layout = QHBoxLayout()
        quest_layout.addWidget(QLabel("Quest ID Filter:"))
        self.quest_filter_edit = QLineEdit()
        self.quest_filter_edit.setPlaceholderText("e.g. XYJEQ005")
        quest_layout.addWidget(self.quest_filter_edit)
        main_layout.addLayout(quest_layout)

        self.extract_btn = QPushButton("Extract Voices")
        self.extract_btn.clicked.connect(self.extract_voices)
        main_layout.addWidget(self.extract_btn)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        main_layout.addWidget(self.log_output)

        self.json_data = None
        self.source_folder = ""
        self.output_folder = ""

    def browse_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select JSON File", "", "JSON Files (*.json)")
        if file_path:
            self.json_path_edit.setText(file_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.json_data = json.load(f)
                self.log("JSON file loaded successfully")
            except Exception as e:
                self.log(f"Error loading JSON: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to load JSON file:\n{str(e)}")

    def browse_source_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Source WEM Folder")
        if folder_path:
            self.source_folder_edit.setText(folder_path)
            self.source_folder = folder_path

    def browse_output_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder_path:
            self.output_folder_edit.setText(folder_path)
            self.output_folder = folder_path

    def log(self, message):
        self.log_output.append(message)
        QApplication.processEvents()

    def extract_voices(self):
        if not self.json_data:
            self.log("Error: JSON data not loaded")
            QMessageBox.warning(self, "Warning", "Please load a valid JSON file first")
            return

        if not self.source_folder or not os.path.exists(self.source_folder):
            self.log("Error: Source folder not selected or invalid")
            QMessageBox.warning(self, "Warning", "Please select a valid source folder")
            return

        if not self.output_folder:
            self.log("Error: Output folder not selected")
            QMessageBox.warning(self, "Warning", "Please select an output folder")
            return

        character_filter = self.char_filter_edit.text().strip().lower()
        quest_filter = self.quest_filter_edit.text().strip()

        self.log("\nStarting extraction...")
        self.log(f"Character filter: {character_filter or 'All'}")
        self.log(f"Quest ID filter: {quest_filter or 'All'}")

        character_data = {}
        files_to_copy = []

        for entry_id, entry_data in self.json_data.items():
            source_file = entry_data.get("sourceFileName", "")
            char_match = re.search(r'VO_[^\\/]+\\VO_([^\\/]+)\\', source_file)
            char_name = char_match.group(1) if char_match else entry_data.get("avatarName", "")
            if character_filter and character_filter != char_name.lower():
                continue
            quest_match = re.search(r'vo_([A-Z0-9]+)_', source_file, re.IGNORECASE)
            quest_id = quest_match.group(1) if quest_match else ""
            if quest_filter and quest_filter != quest_id:
                continue
            filename = entry_id + ".wem"
            if char_name not in character_data:
                character_data[char_name] = {"voice_data": {}, "files": []}
            character_data[char_name]["voice_data"][entry_id] = {
                "voiceContent": entry_data.get("voiceContent", ""),
                "sourceFileName": filename,
                "avatarName": char_name
            }
            files_to_copy.append({
                "char_name": char_name,
                "quest_id": quest_id,
                "filename": filename,
                "source_path": None,
                "dest_path": os.path.join(self.output_folder, char_name, quest_id, filename)
            })

        self.log("\nLocating source files recursively...")
        for root, _, files in os.walk(self.source_folder):
            file_set = set(files)
            for file_info in files_to_copy:
                if file_info["source_path"]:
                    continue
                if file_info["filename"] in file_set:
                    file_info["source_path"] = os.path.join(root, file_info["filename"])
                    self.log(f"Found {file_info['filename']} in {root}")

        self.log("\nProcessing files...")
        total_copied = 0
        char_stats = {}

        for file_info in files_to_copy:
            char_name = file_info["char_name"]
            quest_id = file_info["quest_id"]
            if not file_info["source_path"]:
                self.log(f"File not found: {file_info['filename']}")
                continue
            char_folder = os.path.join(self.output_folder, char_name, quest_id)
            os.makedirs(char_folder, exist_ok=True)
            try:
                shutil.copy2(file_info["source_path"], file_info["dest_path"])
                total_copied += 1
                char_stats[char_name] = char_stats.get(char_name, 0) + 1
            except Exception as e:
                self.log(f"Error copying {file_info['filename']}: {str(e)}")

        for char_name, data in character_data.items():
            char_folder = os.path.join(self.output_folder, char_name)
            json_path = os.path.join(char_folder, "voice_data.json")
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data["voice_data"], f, ensure_ascii=False, indent=2)
                self.log(f"Saved voice data for {char_name}")
            except Exception as e:
                self.log(f"Error saving JSON for {char_name}: {str(e)}")

        self.log("\nExtraction complete!")
        self.log(f"Total files copied: {total_copied}")
        self.log("\nCharacter statistics:")
        for char, count in char_stats.items():
            self.log(f"- {char}: {count} files")

        QMessageBox.information(self, "Complete", "Voice extraction completed successfully!")

if __name__ == "__main__":
    app = QApplication([])
    window = VoiceExtractorApp()
    window.show()
    app.exec()
