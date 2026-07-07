# Disk Cleanup Analyzer

A comprehensive disk cleanup and analysis tool with both CLI and modern GUI interfaces.

## 🚀 Features

- **Duplicate Detection** - Finds files with identical content using MD5 hashing
- **Large File Finder** - Identifies files above a customizable size threshold
- **Temp File Scanner** - Locates temporary, backup, and cache files
- **Unused File Detector** - Finds files not accessed for a specified period
- **Safety First** - Dry run mode shows what would be deleted before actual cleanup
- **Detailed Reports** - Generates both console output and JSON reports
- **Smart Skipping** - Automatically ignores system directories (`.git`, `node_modules`, `.cache`, etc.)
- **Drive Information** - Real-time disk usage, type (SSD/HDD), and capacity
- **Progress Tracking** - Current folder, file count, elapsed time, and ETA
- **Modern GUI** - Professional PySide6 interface with dark theme

## 📋 Requirements

- Python 3.8+
- For GUI: PySide6 (optional, for modern interface)

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/MoDuLah/disk-cleanup-analyzer.git
cd disk-cleanup-analyzer

# Install dependencies (optional for GUI)
pip install -r requirements_pyside6.txt
```

## 💡 Quick Start

### Basic Scan
```bash
# Scan current directory
python3 disk_cleanup_analyzer.py .

# Scan a specific directory
python3 disk_cleanup_analyzer.py /path/to/directory

# Save JSON report
python3 disk_cleanup_analyzer.py . --save-report
```

### Custom Analysis
```bash
# Find files larger than 50MB
python3 disk_cleanup_analyzer.py . --min-size 50

# Find files unused for 2+ years
python3 disk_cleanup_analyzer.py . --min-age 730

# Only find duplicates
python3 disk_cleanup_analyzer.py . --duplicates-only

# Only find large files
python3 disk_cleanup_analyzer.py . --large-only
```

### Safe Cleanup
```bash
# DRY RUN: See what would be deleted (NO actual deletion)
python3 disk_cleanup_analyzer.py . --cleanup /path/to/file1 /path/to/file2

# ACTUAL DELETION: Requires explicit confirmation
python3 disk_cleanup_analyzer.py . --cleanup /path/to/file1 /path/to/file2 --force
```

## 🖥️ GUI Usage

### Classic Tkinter GUI
```bash
# Windows
run_gui.bat

# Linux/macOS
python3 disk_cleanup_gui.py
```

### Modern PySide6 GUI (Recommended)
```bash
# Windows
run_gui_pyside6.bat

# Linux/macOS
python3 disk_cleanup_gui_pyside6.py
```

**Note:** The PySide6 GUI requires additional graphics libraries on Linux:
```bash
# Ubuntu/Debian
sudo apt-get install libegl1 libopengl0 libxcb-cursor0

# macOS (usually included)
pip install PySide6

# Windows (included with PySide6)
pip install PySide6
```

## 📖 Usage Examples

### Example 1: Full Home Directory Scan
```bash
python3 disk_cleanup_analyzer.py ~ --save-report
```
This will scan your entire home directory and save a detailed JSON report.

### Example 2: Find All Duplicates
```bash
python3 disk_cleanup_analyzer.py /var/log --duplicates-only
```
Find duplicate log files in `/var/log`.

### Example 3: Cleanup Temporary Files
```bash
# First, see what would be deleted
python3 disk_cleanup_analyzer.py /tmp --cleanup $(find /tmp -name "*.tmp")

# If satisfied, actually delete
python3 disk_cleanup_analyzer.py /tmp --cleanup $(find /tmp -name "*.tmp") --force
```

### Example 4: Find Very Old Files
```bash
python3 disk_cleanup_analyzer.py ~/Documents --min-age 1095
```
Find files in Documents not accessed in 3+ years.

## 📊 Output Format

The tool provides:
- **Console output**: Real-time progress and summary
- **JSON report**: Detailed findings for programmatic processing
- **Size formatting**: Human-readable sizes (B, KB, MB, GB, TB)

### Sample JSON Report Structure
```json
{
  "scan_path": "/home/user",
  "timestamp": "2026-07-07T10:15:57",
  "total_files": 121,
  "total_size": 1234567,
  "total_size_formatted": "1.17 MB",
  "duplicates": [...],
  "large_files": [...],
  "temp_files": [...],
  "old_unused_files": [...]
}
```

## 🔒 Safety Features

1. **Dry Run Mode**: Always test with `--cleanup` first to see what would be deleted
2. **Explicit Confirmation**: Requires typing "YES" to confirm deletions
3. **Detailed Reporting**: Shows all findings before any action
4. **Smart Exclusions**: Automatically skips system and dependency directories
5. **Error Handling**: Gracefully handles permission issues and locked files
6. **System File Protection**: Blocks deletion from critical directories (C:\Windows, /etc, /usr, etc.)

## 📁 Skipped Directories

The following directories are automatically excluded:
- `.git`, `.svn` (version control)
- `node_modules`, `__pycache__` (dependencies)
- `.venv`, `venv`, `env` (virtual environments)
- `.cache`, `.npm`, `.cargo`, `.pip` (package caches)
- `/proc`, `/sys`, `/dev` (system directories)

## 🎨 Modern GUI Features

The PySide6 GUI includes:
- **Dark theme** with professional styling
- **Real-time progress** with ETA and elapsed time
- **Drive information table** with usage statistics
- **Interactive sliders** for settings
- **Clean, organized layout**
- **Syntax-highlighted logs**
- **Progress bar** with percentage completion

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests.

## 📞 Support

- **Issues**: https://github.com/MoDuLah/disk-cleanup-analyzer/issues
- **Documentation**: See README.md for detailed usage

---

**Built with ❤️ using Python and PySide6**
