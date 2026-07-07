#!/usr/bin/env python3
"""
Disk Cleanup Analyzer - Modern PySide6 GUI
A comprehensive disk cleanup and analysis tool with a modern interface.
"""

import sys
import os
import json
import time
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox, QSlider, QProgressBar,
    QTextEdit, QGroupBox, QFrame, QScrollArea, QSplitter,
    QComboBox, QStatusBar, QToolBar, QMenuBar, QMenu,
    QMessageBox, QProgressDialog, QHeaderView, QTableWidget, QTableWidgetItem
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QTimer, QUrl
from PySide6.QtGui import QFont, QIcon, QAction, QPalette, QColor

# Import the analyzer logic
from disk_cleanup_analyzer import DiskCleanupAnalyzer


class ScanWorker(QObject):
    """Worker thread for disk scanning."""
    progress = Signal(int, int, str)  # current, total, message
    log = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, scan_paths, min_size_mb, min_age_days, scan_options):
        super().__init__()
        self.scan_paths = scan_paths
        self.min_size_mb = min_size_mb
        self.min_age_days = min_age_days
        self.scan_options = scan_options
        self.cancelled = False
        self.analyzer = None

    def run(self):
        try:
            start_time = time.time()
            self.analyzer = DiskCleanupAnalyzer()
            self.analyzer.min_size_mb = self.min_size_mb
            self.analyzer.min_age_days = self.min_age_days

            # Reset results
            self.analyzer.results = {
                'duplicates': [],
                'large_files': [],
                'temp_files': [],
                'old_unused_files': [],
                'summary': {}
            }
            self.analyzer.file_hashes = defaultdict(list)
            self.analyzer.total_size = 0
            self.analyzer.file_count = 0

            total_files_estimate = sum(
                sum(1 for _ in os.walk(path) for __ in _[2])
                for path in self.scan_paths
            )

            # Scan each drive
            for scan_path in self.scan_paths:
                if self.cancelled:
                    break

                self.log.emit(f"\nScanning: {scan_path}")
                self._scan_directory(scan_path, total_files_estimate, start_time)

            # Find duplicates
            if not self.cancelled and self.scan_options.get('duplicates', False):
                self.log.emit("\nFinding duplicates...")
                self.analyzer.find_duplicates()

            # Find large files
            if not self.cancelled and self.scan_options.get('large', False):
                self.log.emit(f"\nFinding large files (>{self.min_size_mb}MB)...")
                self.analyzer.find_large_files()

            # Find temp files
            if not self.cancelled and self.scan_options.get('temp', False):
                self.log.emit("\nFinding temporary files...")
                self.analyzer.find_temp_files()

            # Find old files
            if not self.cancelled and self.scan_options.get('old', False):
                self.log.emit(f"\nFinding files unused for >{self.min_age_days} days...")
                self.analyzer.find_old_unused_files()

            # Generate summary
            if not self.cancelled:
                self.analyzer.generate_summary()

            elapsed = time.time() - start_time
            self.log.emit(f"\n{'=' * 60}")
            self.log.emit("Scan complete!")
            self.log.emit(f"Total files: {self.analyzer.file_count:,}")
            self.log.emit(f"Total size: {self.analyzer.format_size(self.analyzer.total_size)}")
            self.log.emit(f"Time: {elapsed:.1f}s")
            self.log.emit(f"{'=' * 60}")

            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))

    def _scan_directory(self, scan_path, total_files, start_time):
        """Scan a directory with progress tracking."""
        scan_path = Path(scan_path)
        current_file = 0

        for root, dirs, filenames in os.walk(scan_path):
            if self.cancelled:
                break

            dirs[:] = [d for d in dirs if not self.analyzer.should_skip_path(Path(root) / d)]

            for filename in filenames:
                if self.cancelled:
                    break

                filepath = Path(root) / filename
                if not filepath.is_file() or self.analyzer.should_skip_path(filepath):
                    continue

                self.analyzer.file_count += 1
                self.analyzer.total_size += self.analyzer.get_file_size(filepath)
                current_file += 1

                # Update progress every 100 files
                if self.analyzer.file_count % 100 == 0:
                    elapsed = time.time() - start_time
                    files_per_sec = self.analyzer.file_count / elapsed if elapsed > 0 else 0
                    remaining = total_files - self.analyzer.file_count
                    eta = remaining / files_per_sec if files_per_sec > 0 else 0

                    # Format times
                    if elapsed < 60:
                        elapsed_str = f"{elapsed:.0f}s"
                    elif elapsed < 3600:
                        elapsed_str = f"{elapsed/60:.0f}m"
                    else:
                        elapsed_str = f"{elapsed/3600:.1f}h"

                    if eta < 60:
                        eta_str = f"{eta:.0f}s"
                    elif eta < 3600:
                        eta_str = f"{eta/60:.0f}m"
                    else:
                        eta_str = f"{eta/3600:.1f}h"

                    message = (f"Scanning: {Path(root).name} | "
                              f"{self.analyzer.file_count:,} files | "
                              f"Elapsed: {elapsed_str} | ETA: {eta_str}")

                    self.progress.emit(
                        self.analyzer.file_count,
                        total_files,
                        f"{message} | Size: {self.analyzer.format_size(self.analyzer.total_size)}"
                    )

    def cancel(self):
        self.cancelled = True


class ModernDiskCleanupGUI(QMainWindow):
    """Modern PySide6 GUI for Disk Cleanup Analyzer."""

    def __init__(self):
        super().__init__()
        self.worker = None
        self.min_size_mb = 10.0
        self.min_age_days = 365
        self.scan_paths = []
        self.is_scanning = False

        self.init_ui()
        self.apply_modern_style()
        
        # Set a more reasonable default window size that fits on most screens
        self.resize(1000, 700)
        self.setMinimumSize(800, 600)

    def init_ui(self):
        """Initialize the user interface with scrollable areas for small screens."""
        self.setWindowTitle("Disk Cleanup Analyzer - Modern")
        
        # Central widget with scroll area for better fit on small screens
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout with scroll area
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setFrameShape(QScrollArea.NoFrame)
        central_scroll = QWidget()
        main_scroll.setWidget(central_scroll)
        
        main_layout = QVBoxLayout(central_scroll)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Header
        header = QLabel("🗑️ Disk Cleanup Analyzer")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #2c3e50; padding: 10px;")
        main_layout.addWidget(header)

        # Splitter for resizable sections
        splitter = QSplitter(Qt.Vertical)

        # Top section - Drives and Settings
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setSpacing(10)

        # Drives section
        drives_group = QGroupBox("📀 Select Drives to Scan")
        drives_layout = QVBoxLayout(drives_group)

        # Drive info table
        self.drive_table = QTableWidget()
        self.drive_table.setColumnCount(6)
        self.drive_table.setHorizontalHeaderLabels([
            "Select", "Drive", "Type", "Used", "Total", "Usage"
        ])
        self.drive_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.drive_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.drive_table.setEditTriggers(QTableWidget.NoEditTriggers)
        drives_layout.addWidget(self.drive_table)

        # Drive buttons
        drive_buttons = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_drives)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_drives)
        drive_buttons.addWidget(select_all_btn)
        drive_buttons.addWidget(deselect_all_btn)
        drives_layout.addLayout(drive_buttons)

        top_layout.addWidget(drives_group)

        # Settings section
        settings_group = QGroupBox("⚙️ Scan Settings")
        settings_layout = QVBoxLayout(settings_group)

        # Scan options
        options_layout = QHBoxLayout()
        self.check_duplicates = QCheckBox("Duplicates")
        self.check_duplicates.setChecked(True)
        self.check_large = QCheckBox("Large Files")
        self.check_large.setChecked(True)
        self.check_temp = QCheckBox("Temp Files")
        self.check_temp.setChecked(True)
        self.check_old = QCheckBox("Old Files")
        self.check_old.setChecked(True)
        options_layout.addWidget(self.check_duplicates)
        options_layout.addWidget(self.check_large)
        options_layout.addWidget(self.check_temp)
        options_layout.addWidget(self.check_old)
        options_layout.addStretch()
        settings_layout.addLayout(options_layout)

        # Min size slider
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Min file size:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 100)
        self.size_slider.setValue(10)
        self.size_slider.valueChanged.connect(lambda v: self.update_size_label(v))
        size_layout.addWidget(self.size_slider)
        self.size_label = QLabel("10 MB")
        self.size_label.setMinimumWidth(60)
        size_layout.addWidget(self.size_label)
        settings_layout.addLayout(size_layout)

        # Min age slider
        age_layout = QHBoxLayout()
        age_layout.addWidget(QLabel("Min age:"))
        self.age_slider = QSlider(Qt.Horizontal)
        self.age_slider.setRange(30, 3650)
        self.age_slider.setValue(365)
        self.age_slider.valueChanged.connect(lambda v: self.update_age_label(v))
        age_layout.addWidget(self.age_slider)
        self.age_label = QLabel("365 days")
        self.age_label.setMinimumWidth(80)
        age_layout.addWidget(self.age_label)
        settings_layout.addLayout(age_layout)

        top_layout.addWidget(settings_group)

        # Action buttons
        action_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ Start Scan")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.start_btn.clicked.connect(self.start_scan)
        self.start_btn.setEnabled(False)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #ff6b6b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_scan)
        self.stop_btn.setEnabled(False)

        action_layout.addWidget(self.start_btn)
        action_layout.addWidget(self.stop_btn)
        action_layout.addStretch()
        top_layout.addLayout(action_layout)

        splitter.addWidget(top_widget)

        # Bottom section - Progress and Results
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(10)

        # Progress bar
        progress_group = QGroupBox("📊 Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setMinimumHeight(25)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Ready")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        progress_layout.addWidget(self.progress_label)

        bottom_layout.addWidget(progress_group)

        # Results log
        results_group = QGroupBox("📝 Results")
        results_layout = QVBoxLayout(results_group)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Consolas", 10))
        self.results_text.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        results_layout.addWidget(self.results_text)

        bottom_layout.addWidget(results_group)

        splitter.addWidget(bottom_widget)
        splitter.setSizes([400, 400])
        main_layout.addWidget(splitter)

        # Status bar
        self.statusBar().showMessage("Ready")

        # Load drives
        self.load_drives()

    def apply_modern_style(self):
        """Apply modern dark theme styling."""
        # Use system default styling - cleaner and more reliable
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2c3e50;
            }
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
                gridline-color: #bdc3c7;
                selection-background-color: #3498db;
                selection-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                gridline-color: #ecf0f1;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QCheckBox {
                spacing: 5px;
                font-size: 13px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #bdc3c7;
                height: 8px;
                background: #ecf0f1;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #3498db;
                border: 1px solid #2980b9;
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #2980b9;
            }
            QPushButton {
                font-size: 13px;
                padding: 10px 20px;
                border-radius: 5px;
                border: none;
                background-color: #3498db;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
            QProgressBar {
                border: 2px solid #3498db;
                border-radius: 5px;
                text-align: center;
                background-color: #ecf0f1;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 3px;
                padding: 5px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
        
        # Add the scroll area to the main window
        self.setCentralWidget(main_scroll)

    def load_drives(self):
        """Load available drives into the table."""
        drives = self.get_available_drives()
        self.drive_table.setRowCount(len(drives))
        
        # Set column widths for better readability
        self.drive_table.setColumnWidth(0, 50)  # Select column
        self.drive_table.setColumnWidth(1, 80)  # Drive column
        self.drive_table.setColumnWidth(2, 80)  # Type column
        self.drive_table.setColumnWidth(3, 80)  # Used column
        self.drive_table.setColumnWidth(4, 80)  # Total column
        self.drive_table.setColumnWidth(5, 80)  # Usage column

        for i, drive in enumerate(drives):
            # Create a checkbox widget for the first column
            cb = QCheckBox()
            cb.setChecked(False)
            cb.setStyleSheet("""
                QCheckBox {
                    spacing: 5px;
                }
            """)
            self.drive_table.setCellWidget(i, 0, cb)
            
            # Set other columns as text items
            self.drive_table.setItem(i, 1, QTableWidgetItem(drive))

            # Get drive info
            try:
                if os.name == 'nt':
                    import ctypes
                    drive_path = drive.rstrip('\\')
                    if not drive_path.endswith(':'):
                        drive_path += '\\'

                    drive_type_num = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                    drive_type_map = {2: 'Removable', 3: 'Fixed', 4: 'Network', 5: 'CD-ROM', 6: 'RAM Disk'}
                    drive_type = drive_type_map.get(drive_type_num, 'Unknown')

                    total_bytes, free_bytes, _ = ctypes.windll.kernel32.GetDiskFreeSpaceExW(drive_path)
                    total_gb = total_bytes / (1024**3)
                    free_gb = free_bytes / (1024**3)
                    used_gb = (total_bytes - free_bytes) / (1024**3)
                    usage_pct = ((total_bytes - free_bytes) / total_bytes * 100) if total_bytes > 0 else 0
                else:
                    stat = os.statvfs(drive)
                    total_bytes = stat.f_blocks * stat.f_frsize
                    free_bytes = stat.f_bfree * stat.f_frsize
                    total_gb = total_bytes / (1024**3)
                    free_gb = free_bytes / (1024**3)
                    used_gb = (total_bytes - free_bytes) / (1024**3)
                    usage_pct = ((total_bytes - free_bytes) / total_bytes * 100) if total_bytes > 0 else 0
                    drive_type = 'Fixed'

                self.drive_table.setItem(i, 2, QTableWidgetItem(drive_type))
                self.drive_table.setItem(i, 3, QTableWidgetItem(f"{used_gb:.1f} GB"))
                self.drive_table.setItem(i, 4, QTableWidgetItem(f"{total_gb:.1f} GB"))
                self.drive_table.setItem(i, 5, QTableWidgetItem(f"{usage_pct:.0f}%"))

            except Exception:
                self.drive_table.setItem(i, 2, QTableWidgetItem("Unknown"))
                self.drive_table.setItem(i, 3, QTableWidgetItem("-"))
                self.drive_table.setItem(i, 4, QTableWidgetItem("-"))
                self.drive_table.setItem(i, 5, QTableWidgetItem("-"))

    def get_available_drives(self):
        """Get list of available drives."""
        drives = []
        if os.name == 'nt':
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
        else:
            drives = [os.getcwd()]
        return drives

    def select_all_drives(self):
        """Select all drives."""
        for row in range(self.drive_table.rowCount()):
            cb = self.drive_table.cellWidget(row, 0)
            if cb:
                cb.setChecked(True)

    def deselect_all_drives(self):
        """Deselect all drives."""
        for row in range(self.drive_table.rowCount()):
            cb = self.drive_table.cellWidget(row, 0)
            if cb:
                cb.setChecked(False)

    def update_size_label(self, value):
        """Update min size label."""
        self.min_size_mb = float(value)
        self.size_label.setText(f"{value} MB")

    def update_age_label(self, value):
        """Update min age label."""
        self.min_age_days = int(value)
        self.age_label.setText(f"{value} days")

    def start_scan(self):
        """Start the scanning process."""
        # Get selected drives
        self.scan_paths = []
        for row in range(self.drive_table.rowCount()):
            cb = self.drive_table.cellWidget(row, 0)
            if cb and cb.isChecked():
                self.scan_paths.append(self.drive_table.item(row, 1).text())

        if not self.scan_paths:
            QMessageBox.warning(self, "Warning", "Please select at least one drive to scan.")
            return

        # Update UI
        self.is_scanning = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.statusBar().showMessage("Scanning...")
        self.progress_bar.setValue(0)
        self.progress_label.setText("Initializing...")

        # Clear results
        self.results_text.clear()
        self.results_text.append(f"{'=' * 60}")
        self.results_text.append(f"Starting scan on: {', '.join(self.scan_paths)}")
        self.results_text.append(f"Settings: Min size = {self.min_size_mb}MB, Min age = {self.min_age_days} days")
        self.results_text.append(f"{'=' * 60}\n")

        # Start worker thread
        self.worker = ScanWorker(
            self.scan_paths,
            self.min_size_mb,
            self.min_age_days,
            {
                'duplicates': self.check_duplicates.isChecked(),
                'large': self.check_large.isChecked(),
                'temp': self.check_temp.isChecked(),
                'old': self.check_old.isChecked()
            }
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.append_log)
        self.worker.error.connect(self.handle_error)
        self.worker.finished.connect(self.scan_finished)

        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def stop_scan(self):
        """Stop the scanning process."""
        if self.worker:
            self.worker.cancel()
        self.is_scanning = False
        self.append_log("\nScan stopped by user.")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("Stopped")

    def update_progress(self, current, total, message):
        """Update progress bar and label."""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
        self.progress_label.setText(message)
        self.statusBar().showMessage(message)

    def append_log(self, message):
        """Append message to results log."""
        self.results_text.append(message)
        self.results_text.verticalScrollBar().setValue(
            self.results_text.verticalScrollBar().maximum()
        )

    def handle_error(self, error_msg):
        """Handle scan error."""
        self.append_log(f"\n❌ Error: {error_msg}")
        QMessageBox.critical(self, "Error", f"Scan failed: {error_msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.is_scanning = False

    def scan_finished(self):
        """Scan completed successfully."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.is_scanning = False
        self.progress_bar.setValue(100)
        self.progress_label.setText("Scan complete")
        self.statusBar().showMessage("Scan complete")


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = ModernDiskCleanupGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
