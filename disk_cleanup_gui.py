#!/usr/bin/env python3
"""
Disk Cleanup Analyzer - Windows GUI Version
Uses tkinter for a graphical interface
Supports scanning multiple drives
"""

import os
import sys
import time
import hashlib
import json
import threading
import queue
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from tkinter import (
    Tk, ttk, Label, Button, Frame, Scrollbar, Text,
    Checkbutton, IntVar, DoubleVar, Scale, LabelFrame, messagebox,
    filedialog, END, NORMAL, DISABLED,
    X, Y, BOTH, HORIZONTAL,
    LEFT, RIGHT, W,
    StringVar, WORD
)


class DiskCleanupGUI:
    """GUI application for disk cleanup analysis."""

    def __init__(self, root):
        self.root = root
        self.root.title("Disk Cleanup Analyzer")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        # Thread-safe queue for communication from background thread to main thread
        self.thread_queue = queue.Queue()

        # Configuration
        self.min_size_mb = 10.0
        self.min_age_days = 365
        self.scan_paths = []
        self.results = {
            'duplicates': [],
            'large_files': [],
            'temp_files': [],
            'old_unused_files': [],
            'summary': {}
        }
        self.file_hashes = defaultdict(list)
        self.total_size = 0
        self.file_count = 0
        self.all_files = []
        self.is_scanning = False
        
        # Scan type options
        self.scan_duplicates = IntVar(value=1)
        self.scan_large = IntVar(value=1)
        self.scan_temp = IntVar(value=1)
        self.scan_old = IntVar(value=1)
        
        # Cleanup options
        self.enable_cleanup = IntVar(value=0)
        self.dry_run = IntVar(value=1)  # Default to dry run for safety

        # Start polling the queue for thread-safe updates
        self._process_queue()

        # Create UI
        self.create_widgets()

        # Bind keyboard shortcuts
        self.root.bind('<Control-s>', lambda e: self.save_report())
        self.root.bind('<Control-q>', lambda e: self.root.quit())

    def create_widgets(self):
        """Create all UI elements."""
        # Main frame with padding
        main_frame = Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=BOTH, expand=True)

        # Title
        title_frame = Frame(main_frame)
        title_frame.pack(fill=X, pady=(0, 10))

        Label(title_frame, text="Disk Cleanup Analyzer",
              font=('Helvetica', 16, 'bold')).pack(side=LEFT)

        # Status label
        self.status_var = StringVar(value="Ready")
        status_label = Label(title_frame, textvariable=self.status_var,
                             font=('Helvetica', 10), fg='gray')
        status_label.pack(side=RIGHT)

        # Drive selection frame
        drive_frame = LabelFrame(main_frame, text="Select Drives to Scan",
                                 padx=10, pady=10)
        drive_frame.pack(fill=X, pady=(0, 10))

        # Get available drives
        self.available_drives = self.get_available_drives()

        # Create checkboxes for each drive
        self.drive_vars = {}
        for i, drive in enumerate(self.available_drives):
            var = IntVar(value=0)
            cb = Checkbutton(drive_frame, text=drive, variable=var)
            cb.grid(row=i // 4, column=i % 4, sticky=W, padx=5, pady=2)
            self.drive_vars[drive] = var

            # Check first 2 drives by default
            if i < 2:
                var.set(1)

        # "Select All" and "Deselect All" buttons - use grid to match checkboxes
        Button(drive_frame, text="Select All",
               command=lambda: self.set_all_drives(True),
               font=('Helvetica', 9, 'bold')).grid(row=len(self.available_drives) // 4 + 1, column=0, sticky=W, padx=5, pady=10)
        Button(drive_frame, text="Deselect All",
               command=lambda: self.set_all_drives(False),
               font=('Helvetica', 9, 'bold')).grid(row=len(self.available_drives) // 4 + 1, column=1, sticky=W, padx=5, pady=10)

        # Settings frame
        settings_frame = LabelFrame(main_frame, text="Settings", padx=10, pady=10)
        settings_frame.pack(fill=X, pady=(0, 10))

        # Min size slider
        size_frame = Frame(settings_frame)
        size_frame.pack(fill=X, pady=2)

        Label(size_frame, text="Min file size (MB):").pack(side=LEFT)
        self.size_var = DoubleVar(value=self.min_size_mb)
        size_slider = Scale(size_frame, from_=1, to=100, orient=HORIZONTAL,
                            variable=self.size_var, command=self.update_min_size)
        size_slider.pack(side=LEFT, fill=X, expand=True, padx=10)
        self.size_label = Label(size_frame, text=f"{self.min_size_mb:.0f} MB", width=10)
        self.size_label.pack(side=RIGHT)

        # Min age slider
        age_frame = Frame(settings_frame)
        age_frame.pack(fill=X, pady=2)

        Label(age_frame, text="Min age (days):").pack(side=LEFT)
        self.age_var = IntVar(value=self.min_age_days)
        age_slider = Scale(age_frame, from_=30, to=3650, orient=HORIZONTAL,
                           variable=self.age_var, command=self.update_min_age)
        age_slider.pack(side=LEFT, fill=X, expand=True, padx=10)
        self.age_label = Label(age_frame, text=f"{self.min_age_days} days", width=12)
        self.age_label.pack(side=RIGHT)

        # Scan type options frame
        scan_options_frame = LabelFrame(main_frame, text="Scan Options", padx=10, pady=10)
        scan_options_frame.pack(fill=X, pady=(0, 10))

        # Create checkboxes for scan types
        Checkbutton(scan_options_frame, text="Find Duplicates", variable=self.scan_duplicates).pack(anchor=W)
        Checkbutton(scan_options_frame, text="Find Large Files", variable=self.scan_large).pack(anchor=W)
        Checkbutton(scan_options_frame, text="Find Temp Files", variable=self.scan_temp).pack(anchor=W)
        Checkbutton(scan_options_frame, text="Find Old Unused Files", variable=self.scan_old).pack(anchor=W)

        # Cleanup options frame
        cleanup_frame = LabelFrame(main_frame, text="Cleanup Options", padx=10, pady=10)
        cleanup_frame.pack(fill=X, pady=(0, 10))

        Checkbutton(cleanup_frame, text="Enable Cleanup Mode", variable=self.enable_cleanup,
                    command=self.toggle_cleanup_options).pack(anchor=W)
        
        self.dry_run_checkbox = Checkbutton(cleanup_frame, text="Test Run (Preview only - NO deletion)", 
                                            variable=self.dry_run, state=DISABLED)
        self.dry_run_checkbox.pack(anchor=W)

        # Action buttons
        button_frame = Frame(main_frame)
        button_frame.pack(fill=X, pady=(0, 10))

        self.scan_button = Button(button_frame, text="Start Scan",
                                  command=self.start_scan,
                                  font=('Helvetica', 11, 'bold'), width=15)
        self.scan_button.pack(side=LEFT, padx=5)

        self.stop_button = Button(button_frame, text="Stop",
                                  command=self.stop_scan, state=DISABLED,
                                  width=10)
        self.stop_button.pack(side=LEFT, padx=5)

        Button(button_frame, text="Save Report",
               command=self.save_report, width=15).pack(side=LEFT, padx=5)

        Button(button_frame, text="Exit",
               command=self.root.quit, width=10).pack(side=RIGHT, padx=5)
        
        # Cleanup button (initially disabled)
        self.cleanup_button = Button(button_frame, text="Clean Selected",
                                     command=self.start_cleanup, state=DISABLED,
                                     width=15, fg='red')
        self.cleanup_button.pack(side=RIGHT, padx=5)

        # Results text area with scrollbar
        results_frame = Frame(main_frame)
        results_frame.pack(fill=BOTH, expand=True)

        scrollbar = Scrollbar(results_frame)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.results_text = Text(results_frame, wrap=WORD, font=('Consolas', 10),
                                 yscrollcommand=scrollbar.set, state=DISABLED)
        self.results_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=self.results_text.yview)

        # Progress bar
        self.progress_var = DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var,
                                            maximum=100, mode='determinate')
        self.progress_bar.pack(fill=X, pady=(10, 0))

        # Status text
        self.progress_label = Label(main_frame, text="0 files scanned",
                                    font=('Helvetica', 9), fg='gray')
        self.progress_label.pack(fill=X, pady=(2, 0))

        # Initialize with welcome message
        self.log("Welcome to Disk Cleanup Analyzer!")
        self.log(f"Available drives: {', '.join(self.available_drives)}")
        self.log("Select drives and click 'Start Scan' to begin analysis.")
        self.log("")

    def get_available_drives(self):
        """Get list of available drives on Windows."""
        drives = []
        if sys.platform == 'win32':
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                drive = f"{letter}:\\\\"
                if os.path.exists(drive):
                    drives.append(drive)
        else:
            drives = [os.getcwd()]
        return drives

    def set_all_drives(self, value):
        """Set all drive checkboxes to value."""
        for var in self.drive_vars.values():
            var.set(1 if value else 0)

    def toggle_cleanup_options(self):
        """Enable/disable cleanup options based on enable_cleanup checkbox."""
        if self.enable_cleanup.get():
            self.dry_run_checkbox.config(state=NORMAL)
            self.cleanup_button.config(state=NORMAL)
            self.log("\n⚠ Cleanup mode enabled. Ensure 'Test Run' is checked for safety!")
        else:
            self.dry_run_checkbox.config(state=DISABLED)
            self.cleanup_button.config(state=DISABLED)

    def update_min_size(self, value):
        """Update minimum file size setting."""
        self.min_size_mb = float(value)
        self.size_label.config(text=f"{self.min_size_mb:.0f} MB")

    def update_min_age(self, value):
        """Update minimum age setting."""
        self.min_age_days = int(value)
        self.age_label.config(text=f"{self.min_age_days} days")

    def _process_queue(self):
        """Process messages from the thread-safe queue (called on main thread)."""
        try:
            while True:
                msg = self.thread_queue.get_nowait()
                if msg['type'] == 'log':
                    self.results_text.config(state=NORMAL)
                    self.results_text.insert(END, msg['text'] + "\n")
                    self.results_text.see(END)
                    self.results_text.config(state=DISABLED)
                elif msg['type'] == 'progress':
                    total = msg['total']
                    current = msg['current']
                    message = msg.get('message', '')
                    if total > 0:
                        percent = (current / total) * 100
                    else:
                        percent = 0
                    self.progress_var.set(percent)
                    self.progress_label.config(text=f"{current} files scanned - {message}")
                    self.root.update_idletasks()
                elif msg['type'] == 'update_status':
                    self.status_var.set(msg['text'])
        except queue.Empty:
            pass
        finally:
            # Continue polling
            self.root.after(50, self._process_queue)

    def log(self, message):
        """Add message to results text area (thread-safe)."""
        self.thread_queue.put({'type': 'log', 'text': message})

    def update_progress(self, current, total, message=""):
        """Update progress bar and label (thread-safe)."""
        self.thread_queue.put({
            'type': 'progress',
            'current': current,
            'total': total,
            'message': message
        })

    def update_status(self, text):
        """Update status label (thread-safe)."""
        self.thread_queue.put({'type': 'update_status', 'text': text})

    def start_scan(self):
        """Start the scanning process in a background thread."""
        if self.is_scanning:
            return

        # Get selected drives
        self.scan_paths = [drive for drive, var in self.drive_vars.items() if var.get()]

        if not self.scan_paths:
            messagebox.showwarning("Warning", "Please select at least one drive to scan.")
            return

        # Update UI
        self.is_scanning = True
        self.scan_button.config(state=DISABLED)
        self.stop_button.config(state=NORMAL)
        self.update_status("Scanning...")
        self.log(f"\n{'=' * 60}")
        self.log(f"Starting scan on: {', '.join(self.scan_paths)}")
        self.log(f"Settings: Min size = {self.min_size_mb}MB, Min age = {self.min_age_days} days")
        self.log(f"{'=' * 60}\n")

        # Run scan in background thread
        thread = threading.Thread(target=self.run_scan, daemon=True)
        thread.start()

    def stop_scan(self):
        """Stop the scanning process."""
        self.is_scanning = False
        self.log("\nScan stopped by user.")
        self.scan_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)
        self.update_status("Stopped")

    def run_scan(self):
        """Run the actual scanning process."""
        try:
            # Reset results
            self.results = {
                'duplicates': [],
                'large_files': [],
                'temp_files': [],
                'old_unused_files': [],
                'summary': {}
            }
            self.file_hashes = defaultdict(list)
            self.total_size = 0
            self.file_count = 0
            self.all_files = []

            # Scan each drive
            for scan_path in self.scan_paths:
                if not self.is_scanning:
                    break

                self.log(f"\nScanning: {scan_path}")
                self.scan_directory(scan_path)

            # Find duplicates (if selected)
            if self.is_scanning and self.scan_duplicates.get():
                self.log("\nFinding duplicates...")
                self.find_duplicates()
            elif self.is_scanning:
                self.results['duplicates'] = []

            # Find large files (if selected)
            if self.is_scanning and self.scan_large.get():
                self.log(f"\nFinding large files (>{self.min_size_mb}MB)...")
                self.find_large_files()
            elif self.is_scanning:
                self.results['large_files'] = []

            # Find temp files (if selected)
            if self.is_scanning and self.scan_temp.get():
                self.log("\nFinding temporary files...")
                self.find_temp_files()
            elif self.is_scanning:
                self.results['temp_files'] = []

            # Find old unused files (if selected)
            if self.is_scanning and self.scan_old.get():
                self.log(f"\nFinding files unused for >{self.min_age_days} days...")
                self.find_old_unused_files()
            elif self.is_scanning:
                self.results['old_unused_files'] = []

            # Generate summary
            if self.is_scanning:
                self.generate_summary()

            self.log(f"\n{'=' * 60}")
            self.log("Scan complete!")
            self.log(f"Total files: {self.file_count}")
            self.log(f"Total size: {self.format_size(self.total_size)}")
            self.log(f"{'=' * 60}")

        except Exception as e:
            self.log(f"\nError: {e}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            self.is_scanning = False
            self.scan_button.config(state=NORMAL)
            self.stop_button.config(state=DISABLED)
            self.update_status("Ready")
            self.progress_var.set(100)
            self.progress_label.config(text="Scan complete")

    def scan_directory(self, scan_path):
        """Scan a directory for files."""
        scan_path = Path(scan_path)

        for root, dirs, filenames in os.walk(scan_path):
            if not self.is_scanning:
                break

            # Filter out skip directories
            dirs[:] = [d for d in dirs if not self.should_skip_path(Path(root) / d)]

            for filename in filenames:
                if not self.is_scanning:
                    break

                filepath = Path(root) / filename
                if not filepath.is_file():
                    continue
                if self.should_skip_path(filepath):
                    continue

                self.file_count += 1
                self.total_size += self.get_file_size(filepath)
                self.all_files.append(filepath)

                # Update progress every 1000 files
                if self.file_count % 1000 == 0:
                    self.update_progress(self.file_count, self.file_count,
                                         f"Size: {self.format_size(self.total_size)}")

        self.update_progress(self.file_count, self.file_count,
                             f"Total: {self.format_size(self.total_size)}")

    def should_skip_path(self, filepath):
        """Determine if path should be skipped."""
        skip_dirs = {
            '.git', '.svn', 'node_modules', '__pycache__', '.venv', 'venv',
            '.hermes', '.cache', '.local', '.npm', '.cargo', '.pip',
            'virtualenv', 'env', 'ENV', '.rbenv', '.gem'
        }

        for part in filepath.parts:
            if part.startswith('.') or part in skip_dirs:
                return True

        try:
            filepath_str = str(filepath)
            if any(system in filepath_str for system in ['/proc/', '/sys/', '/dev/']):
                return True
        except (IOError, OSError):
            return True

        return False

    def get_file_size(self, filepath):
        """Get file size in bytes."""
        try:
            return filepath.stat().st_size
        except (IOError, OSError):
            return 0

    def get_file_age_days(self, filepath):
        """Get file age in days."""
        try:
            stat = filepath.stat()
            atime = stat.st_atime
            now = time.time()
            return (now - atime) / (24 * 3600)
        except (IOError, OSError):
            return 0

    def calculate_file_hash(self, filepath, chunk_size=8192):
        """Calculate MD5 hash of file."""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, OSError):
            return None

    def is_temp_file(self, filepath):
        """Check if file is temporary."""
        temp_patterns = [
            '.tmp', '.temp', '.swp', '.bak', '.backup', '~',
            '.cache', '.log', '.old', '.orig', '.rej'
        ]
        name = filepath.name.lower()
        return any(pattern in name for pattern in temp_patterns)

    def find_duplicates(self):
        """Find duplicate files."""
        # Group by size
        size_groups = defaultdict(list)
        for filepath in self.all_files:
            size = self.get_file_size(filepath)
            if size > 0:
                size_groups[size].append(filepath)

        # Hash files with matching sizes
        for size, file_list in size_groups.items():
            if len(file_list) < 2:
                continue

            for filepath in file_list:
                file_hash = self.calculate_file_hash(filepath)
                if file_hash:
                    self.file_hashes[(file_hash, size)].append(filepath)

        # Collect duplicates
        duplicates = []
        for (file_hash, size), file_list in self.file_hashes.items():
            if len(file_list) > 1:
                duplicates.append({
                    'hash': file_hash,
                    'size': size,
                    'count': len(file_list),
                    'files': [str(f) for f in file_list],
                    'wasted_space': size * (len(file_list) - 1)
                })

        self.results['duplicates'] = duplicates
        self.log(f"  Found {len(duplicates)} duplicate groups")

    def find_large_files(self):
        """Find large files."""
        min_size_bytes = int(self.min_size_mb * 1024 * 1024)
        large_files = []

        for filepath in self.all_files:
            size = self.get_file_size(filepath)
            if size >= min_size_bytes:
                large_files.append({
                    'path': str(filepath),
                    'size': size,
                    'size_mb': size / (1024 * 1024)
                })

        large_files.sort(key=lambda x: x['size'], reverse=True)
        self.results['large_files'] = large_files
        self.log(f"  Found {len(large_files)} large files")

    def find_temp_files(self):
        """Find temporary files."""
        temp_files = []
        for filepath in self.all_files:
            if self.is_temp_file(filepath):
                temp_files.append({
                    'path': str(filepath),
                    'size': self.get_file_size(filepath),
                    'type': 'temp'
                })

        self.results['temp_files'] = temp_files
        self.log(f"  Found {len(temp_files)} temp files")

    def find_old_unused_files(self):
        """Find old unused files."""
        old_files = []
        for filepath in self.all_files:
            age_days = self.get_file_age_days(filepath)
            if age_days > self.min_age_days:
                old_files.append({
                    'path': str(filepath),
                    'size': self.get_file_size(filepath),
                    'age_days': int(age_days),
                    'last_access': datetime.fromtimestamp(filepath.stat().st_atime).strftime('%Y-%m-%d')
                })

        old_files.sort(key=lambda x: x['age_days'], reverse=True)
        self.results['old_unused_files'] = old_files
        self.log(f"  Found {len(old_files)} old unused files")

    def generate_summary(self):
        """Generate and display summary."""
        self.log("\nSUMMARY")
        self.log("-" * 60)

        potential_savings = 0
        potential_savings += sum(d['wasted_space'] for d in self.results['duplicates'])
        potential_savings += sum(f['size'] for f in self.results['temp_files'])
        potential_savings += sum(f['size'] for f in self.results['old_unused_files'])

        self.log(f"Duplicate groups: {len(self.results['duplicates'])}")
        self.log(f"Large files: {len(self.results['large_files'])}")
        self.log(f"Temp files: {len(self.results['temp_files'])}")
        self.log(f"Old unused files: {len(self.results['old_unused_files'])}")
        self.log(f"\nPOTENTIAL SPACE RECOVERY: {self.format_size(potential_savings)}")

    def format_size(self, bytes_val):
        """Format bytes to human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(bytes_val) < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"

    def save_report(self):
        """Save analysis results to JSON file."""
        if not self.results.get('duplicates') and not self.results.get('large_files'):
            messagebox.showinfo("Info", "No results to save. Run a scan first.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Report"
        )

        if filename:
            output = {
                'scan_paths': self.scan_paths,
                'timestamp': datetime.now().isoformat(),
                'total_files': self.file_count,
                'total_size': self.total_size,
                'total_size_formatted': self.format_size(self.total_size),
                'duplicates': self.results['duplicates'],
                'large_files': self.results['large_files'],
                'temp_files': self.results['temp_files'],
                'old_unused_files': self.results['old_unused_files']
            }

            with open(filename, 'w') as f:
                json.dump(output, f, indent=2)

            self.log(f"\nReport saved to: {filename}")
            messagebox.showinfo("Success", f"Report saved to:\n{filename}")

    def cleanup_selected(self):
        """Delete selected files (placeholder for now)."""
        messagebox.showinfo("Cleanup",
                            "File cleanup feature coming soon!\n\n"
                            "For now, use the command-line version:\n"
                            "python disk_cleanup_analyzer.py --cleanup <file1> <file2> --force")

    def start_cleanup(self):
        """Start the cleanup process based on scan results."""
        if not self.enable_cleanup.get():
            messagebox.showwarning("Warning", "Please enable cleanup mode first.")
            return

        # Collect all files to potentially delete
        files_to_delete = []
        
        # Add duplicates (keep first, mark rest for deletion)
        for dup_group in self.results.get('duplicates', []):
            # Skip the first file in each group (keep it)
            for filepath in dup_group['files'][1:]:
                files_to_delete.append({
                    'path': filepath,
                    'size': dup_group['size'],
                    'reason': f"Duplicate of {dup_group['files'][0]}"
                })
        
        # Add large files
        for large_file in self.results.get('large_files', []):
            files_to_delete.append({
                'path': large_file['path'],
                'size': large_file['size'],
                'reason': f"Large file ({large_file['size_mb']:.2f} MB)"
            })
        
        # Add temp files
        for temp_file in self.results.get('temp_files', []):
            files_to_delete.append({
                'path': temp_file['path'],
                'size': temp_file['size'],
                'reason': "Temporary file"
            })
        
        # Add old unused files
        for old_file in self.results.get('old_unused_files', []):
            files_to_delete.append({
                'path': old_file['path'],
                'size': old_file['size'],
                'reason': f"Unused for {old_file['age_days']} days"
            })

        if not files_to_delete:
            messagebox.showinfo("Info", "No files selected for cleanup based on your scan options.")
            return

        # Calculate total space to be freed
        total_space = sum(f['size'] for f in files_to_delete)
        
        # Show preview
        if self.dry_run.get():
            # DRY RUN - just show what WOULD be deleted
            preview_msg = f"🔍 TEST RUN - NO FILES WILL BE DELETED\n\n"
            preview_msg += f"Files that would be deleted: {len(files_to_delete)}\n"
            preview_msg += f"Total space to be freed: {self.format_size(total_space)}\n\n"
            preview_msg += "-" * 60 + "\n\n"
            
            # Show first 10 files as preview
            for i, f in enumerate(files_to_delete[:10], 1):
                preview_msg += f"{i}. {f['path']}\n   Reason: {f['reason']}\n   Size: {self.format_size(f['size'])}\n\n"
            
            if len(files_to_delete) > 10:
                preview_msg += f"... and {len(files_to_delete) - 10} more files\n"
            
            preview_msg += "\n" + "=" * 60 + "\n"
            preview_msg += "✅ This is a TEST RUN - No files will actually be deleted!\n"
            preview_msg += "To actually delete, uncheck 'Test Run' and click Clean Selected again."
            
            messagebox.showinfo("Test Run Preview", preview_msg)
            self.log(f"\n🔍 TEST RUN: {len(files_to_delete)} files would be deleted ({self.format_size(total_space)})")
            self.log("No files were actually deleted - this was just a preview!")
        else:
            # ACTUAL DELETION - require confirmation
            confirm_msg = f"⚠️  WARNING: This will PERMANENTLY DELETE files!\n\n"
            confirm_msg += f"Files to delete: {len(files_to_delete)}\n"
            confirm_msg += f"Total space to free: {self.format_size(total_space)}\n\n"
            confirm_msg += "-" * 60 + "\n\n"
            
            # Show first 5 files
            for i, f in enumerate(files_to_delete[:5], 1):
                confirm_msg += f"{i}. {f['path']}\n"
            
            if len(files_to_delete) > 5:
                confirm_msg += f"... and {len(files_to_delete) - 5} more files\n"
            
            confirm_msg += "\n" + "=" * 60 + "\n"
            confirm_msg += "Are you SURE you want to proceed?\n"
            confirm_msg += "This action CANNOT be undone!"
            
            if messagebox.askyesno("Confirm Deletion", confirm_msg, icon='warning'):
                # Actually delete the files
                deleted_count = 0
                failed_count = 0
                
                self.log(f"\n{'=' * 60}")
                self.log("BEGINNING ACTUAL DELETION...")
                self.log(f"{'=' * 60}\n")
                
                for f in files_to_delete:
                    try:
                        os.remove(f['path'])
                        deleted_count += 1
                        self.log(f"✅ Deleted: {f['path']}")
                    except Exception as e:
                        failed_count += 1
                        self.log(f"❌ Failed to delete: {f['path']} - {str(e)}")
                
                self.log(f"\n{'=' * 60}")
                self.log(f"DELETION COMPLETE")
                self.log(f"Successfully deleted: {deleted_count} files")
                if failed_count > 0:
                    self.log(f"Failed to delete: {failed_count} files")
                self.log(f"Total space freed: {self.format_size(total_space)}")
                self.log(f"{'=' * 60}\n")
                
                messagebox.showinfo("Cleanup Complete", 
                                    f"Successfully deleted {deleted_count} files.\n"
                                    f"Failed to delete {failed_count} files.\n"
                                    f"Total space freed: {self.format_size(total_space)}")
            else:
                self.log("\n❌ Deletion cancelled by user.")
                messagebox.showinfo("Cancelled", "Deletion was cancelled.")


def main():
    """Main entry point."""
    root = Tk()
    app = DiskCleanupGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
