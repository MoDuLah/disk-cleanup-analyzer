#!/usr/bin/env python3
"""
Disk Cleanup Analyzer - Comprehensive file analysis and cleanup tool
Identifies: duplicates, large files, temp files, unused/old files
SAFETY FIRST: Shows all findings, requires explicit confirmation before deletion
"""

import os
import hashlib
import json
import time
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

class DiskCleanupAnalyzer:
    """Analyze disk for redundant, duplicate, and unused files."""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
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
        
    def calculate_file_hash(self, filepath: Path, chunk_size: int = 8192) -> str:
        """Calculate MD5 hash of file content for duplicate detection."""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, OSError):
            return None
    
    def get_file_size(self, filepath: Path) -> int:
        """Get file size in bytes."""
        try:
            return filepath.stat().st_size
        except (IOError, OSError):
            return 0
    
    def get_file_age_days(self, filepath: Path) -> float:
        """Get file age in days based on last access time."""
        try:
            stat = filepath.stat()
            # Use last access time (atime), fall back to mtime
            atime = stat.st_atime
            now = time.time()
            return (now - atime) / (24 * 3600)
        except (IOError, OSError):
            return 0
    
    def is_temp_file(self, filepath: Path) -> bool:
        """Check if file is a temporary/cache file."""
        temp_patterns = [
            '.tmp', '.temp', '.swp', '.bak', '.backup', '~',
            '.cache', '.log', '.old', '.orig', '.rej', '.orig'
        ]
        name = filepath.name.lower()
        return any(pattern in name for pattern in temp_patterns)
    
    def should_skip_path(self, filepath: Path) -> bool:
        """Determine if path should be skipped."""
        skip_dirs = {
            '.git', '.svn', 'node_modules', '__pycache__', '.venv', 'venv',
            '.hermes', '.cache', '.local', '.npm', '.cargo', '.pip',
            'virtualenv', 'env', 'ENV', '.rbenv', '.gem'
        }
        
        # Skip hidden directories and common dependency directories
        for part in filepath.parts:
            if part.startswith('.') or part in skip_dirs:
                return True
        
        # Skip system directories
        try:
            filepath_str = str(filepath)
            if any(system in filepath_str for system in ['/proc/', '/sys/', '/dev/']):
                return True
        except (IOError, OSError):
            return True
            
        return False
    
    def scan_files(self) -> List[Path]:
        """Scan directory for all files."""
        files = []
        print(f"\n🔍 Scanning: {self.root_path}")
        
        for root, dirs, filenames in os.walk(self.root_path):
            # Filter out skip directories
            dirs[:] = [d for d in dirs if not self.should_skip_path(Path(root) / d)]
            
            for filename in filenames:
                filepath = Path(root) / filename
                if not filepath.is_file():
                    continue
                if self.should_skip_path(filepath):
                    continue
                    
                files.append(filepath)
                self.file_count += 1
                self.total_size += self.get_file_size(filepath)
                
                # Progress indicator
                if self.file_count % 1000 == 0:
                    print(f"  Scanned {self.file_count} files...")
        
        print(f"  ✓ Found {self.file_count} files ({self.format_size(self.total_size)})")
        return files
    
    def find_duplicates(self, files: List[Path]) -> List[Dict]:
        """Find duplicate files based on size and content hash."""
        print("\n🔍 Finding duplicates...")
        
        # Group by size first (faster than hashing everything)
        size_groups = defaultdict(list)
        for filepath in files:
            size = self.get_file_size(filepath)
            if size > 0:  # Skip empty files
                size_groups[size].append(filepath)
        
        # Only hash files with matching sizes
        duplicate_groups = []
        for size, file_list in size_groups.items():
            if len(file_list) < 2:
                continue
                
            # Calculate hashes for files with same size
            for filepath in file_list:
                file_hash = self.calculate_file_hash(filepath)
                if file_hash:
                    self.file_hashes[(file_hash, size)].append(filepath)
        
        # Collect duplicate groups
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
        print(f"  ✓ Found {len(duplicates)} duplicate groups ({self.format_size(sum(d['wasted_space'] for d in duplicates))} wasted)")
        return duplicates
    
    def find_large_files(self, files: List[Path], min_size_mb: float = 10.0) -> List[Dict]:
        """Find files larger than threshold."""
        print(f"\n🔍 Finding large files (>{min_size_mb}MB)...")
        
        min_size_bytes = int(min_size_mb * 1024 * 1024)
        large_files = []
        
        for filepath in files:
            size = self.get_file_size(filepath)
            if size >= min_size_bytes:
                large_files.append({
                    'path': str(filepath),
                    'size': size,
                    'size_mb': size / (1024 * 1024)
                })
        
        # Sort by size descending
        large_files.sort(key=lambda x: x['size'], reverse=True)
        self.results['large_files'] = large_files
        print(f"  ✓ Found {len(large_files)} large files ({self.format_size(sum(f['size'] for f in large_files))})")
        return large_files
    
    def find_temp_files(self, files: List[Path]) -> List[Dict]:
        """Find temporary and cache files."""
        print("\n🔍 Finding temporary files...")
        
        temp_files = []
        for filepath in files:
            if self.is_temp_file(filepath):
                temp_files.append({
                    'path': str(filepath),
                    'size': self.get_file_size(filepath),
                    'type': 'temp'
                })
        
        self.results['temp_files'] = temp_files
        print(f"  ✓ Found {len(temp_files)} temp/cache files ({self.format_size(sum(f['size'] for f in temp_files))})")
        return temp_files
    
    def find_old_unused_files(self, files: List[Path], min_days: int = 365) -> List[Dict]:
        """Find files not accessed in specified days."""
        print(f"\n🔍 Finding files unused for >{min_days} days...")
        
        old_files = []
        for filepath in files:
            age_days = self.get_file_age_days(filepath)
            if age_days > min_days:
                old_files.append({
                    'path': str(filepath),
                    'size': self.get_file_size(filepath),
                    'age_days': int(age_days),
                    'last_access': datetime.fromtimestamp(filepath.stat().st_atime).strftime('%Y-%m-%d')
                })
        
        # Sort by age descending
        old_files.sort(key=lambda x: x['age_days'], reverse=True)
        self.results['old_unused_files'] = old_files
        print(f"  ✓ Found {len(old_files)} unused files ({self.format_size(sum(f['size'] for f in old_files))})")
        return old_files
    
    def format_size(self, bytes_val: int) -> str:
        """Format bytes to human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(bytes_val) < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"
    
    def generate_report(self) -> str:
        """Generate detailed analysis report."""
        report = []
        report.append("=" * 80)
        report.append("DISK CLEANUP ANALYSIS REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Scanned: {self.root_path}")
        report.append(f"Total Files: {self.file_count}")
        report.append(f"Total Size: {self.format_size(self.total_size)}")
        report.append("=" * 80)
        
        # Duplicates section
        if self.results['duplicates']:
            report.append("\n📁 DUPLICATE FILES")
            report.append("-" * 40)
            total_wasted = 0
            for i, dup in enumerate(self.results['duplicates'][:20], 1):  # Show first 20
                report.append(f"\nGroup {i}: {dup['count']} copies, {self.format_size(dup['size'])} each")
                report.append(f"  Wasted: {self.format_size(dup['wasted_space'])}")
                for f in dup['files']:
                    report.append(f"    • {f}")
                total_wasted += dup['wasted_space']
            
            if len(self.results['duplicates']) > 20:
                report.append(f"\n  ... and {len(self.results['duplicates']) - 20} more groups")
            
            report.append(f"\n📊 Total wasted by duplicates: {self.format_size(total_wasted)}")
        
        # Large files section
        if self.results['large_files']:
            report.append("\n📦 LARGE FILES (>10MB)")
            report.append("-" * 40)
            for i, f in enumerate(self.results['large_files'][:20], 1):
                report.append(f"  {i}. {self.format_size(f['size']):>10}  {f['path']}")
            
            if len(self.results['large_files']) > 20:
                report.append(f"\n  ... and {len(self.results['large_files']) - 20} more files")
            
            report.append(f"\n📊 Total large files: {self.format_size(sum(f['size'] for f in self.results['large_files']))}")
        
        # Temp files section
        if self.results['temp_files']:
            report.append("\n🗑️  TEMPORARY/BACKUP FILES")
            report.append("-" * 40)
            report.append(f"  Count: {len(self.results['temp_files'])}")
            report.append(f"  Total size: {self.format_size(sum(f['size'] for f in self.results['temp_files']))}")
            
            # Show sample
            report.append("\n  Sample:")
            for f in self.results['temp_files'][:10]:
                report.append(f"    • {f['path']} ({self.format_size(f['size'])})")
        
        # Old unused files section
        if self.results['old_unused_files']:
            report.append("\n📅 UNUSED FILES (>365 days)")
            report.append("-" * 40)
            report.append(f"  Count: {len(self.results['old_unused_files'])}")
            report.append(f"  Total size: {self.format_size(sum(f['size'] for f in self.results['old_unused_files']))}")
            
            # Show oldest 10
            report.append("\n  Oldest files:")
            for f in self.results['old_unused_files'][:10]:
                report.append(f"    • {f['path']}")
                report.append(f"      Size: {self.format_size(f['size'])}, Last accessed: {f['last_access']} ({f['age_days']} days ago)")
        
        # Summary
        report.append("\n" + "=" * 80)
        report.append("SUMMARY")
        report.append("=" * 80)
        
        potential_savings = 0
        potential_savings += sum(d['wasted_space'] for d in self.results['duplicates'])
        potential_savings += sum(f['size'] for f in self.results['temp_files'])
        potential_savings += sum(f['size'] for f in self.results['old_unused_files'])
        
        report.append(f"Duplicate groups: {len(self.results['duplicates'])}")
        report.append(f"Large files: {len(self.results['large_files'])}")
        report.append(f"Temp files: {len(self.results['temp_files'])}")
        report.append(f"Old unused files: {len(self.results['old_unused_files'])}")
        report.append(f"\n💰 POTENTIAL SPACE RECOVERY: {self.format_size(potential_savings)}")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_report(self, filename: str = "disk_cleanup_report.json"):
        """Save analysis results to JSON file."""
        output = {
            'scan_path': str(self.root_path),
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
        
        print(f"\n💾 Report saved to: {filename}")
    
    def cleanup_files(self, file_paths: List[str], dry_run: bool = True) -> Tuple[int, int]:
        """
        Delete specified files.
        
        Args:
            file_paths: List of file paths to delete
            dry_run: If True, only show what would be deleted without actually deleting
        
        Returns:
            Tuple of (files_deleted, bytes_freed)
        """
        deleted = 0
        freed = 0
        
        if dry_run:
            print("\n🔍 DRY RUN - No files will be deleted")
            print("-" * 40)
        
        for filepath_str in file_paths:
            filepath = Path(filepath_str)
            try:
                size = self.get_file_size(filepath)
                
                if dry_run:
                    print(f"  Would delete: {filepath} ({self.format_size(size)})")
                else:
                    filepath.unlink()
                    print(f"  Deleted: {filepath} ({self.format_size(size)})")
                
                deleted += 1
                freed += size
                
            except (IOError, OSError) as e:
                print(f"  ❌ Failed to delete {filepath}: {e}")
        
        if not dry_run:
            print(f"\n✅ Cleanup complete: {deleted} files deleted, {self.format_size(freed)} freed")
        else:
            print(f"\n📊 Dry run complete: {deleted} files would be deleted, {self.format_size(freed)} would be freed")
        
        return deleted, freed


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Disk Cleanup Analyzer")
    parser.add_argument('path', nargs='?', default='.', help="Path to analyze (default: current directory)")
    parser.add_argument('--large-only', action='store_true', help="Only find large files")
    parser.add_argument('--duplicates-only', action='store_true', help="Only find duplicates")
    parser.add_argument('--min-size', type=float, default=10.0, help="Minimum size for large files in MB (default: 10)")
    parser.add_argument('--min-age', type=int, default=365, help="Minimum days for unused files (default: 365)")
    parser.add_argument('--save-report', action='store_true', help="Save report to JSON file")
    parser.add_argument('--cleanup', nargs='*', help="Delete specified files (space-separated paths)")
    parser.add_argument('--force', action='store_true', help="Skip confirmation for cleanup")
    
    args = parser.parse_args()
    
    if args.cleanup:
        # Cleanup mode
        analyzer = DiskCleanupAnalyzer(args.path)
        if not args.force:
            print("\n⚠️  WARNING: You are about to delete files!")
            response = input("Type 'YES' to confirm: ")
            if response != 'YES':
                print("❌ Cleanup cancelled.")
                return
        analyzer.cleanup_files(args.cleanup, dry_run=False)
        return
    
    # Analysis mode
    analyzer = DiskCleanupAnalyzer(args.path)
    
    # Scan all files
    files = analyzer.scan_files()
    
    # Run analysis based on options
    if not args.duplicates_only:
        analyzer.find_large_files(files, args.min_size)
        analyzer.find_temp_files(files)
        analyzer.find_old_unused_files(files, args.min_age)
    
    if not args.large_only:
        analyzer.find_duplicates(files)
    
    # Generate and display report
    report = analyzer.generate_report()
    print("\n" + report)
    
    if args.save_report:
        analyzer.save_report()
    
    print("\n💡 Tips:")
    print("  • Review duplicates carefully before deleting")
    print("  • Keep one copy of each duplicate group")
    print("  • Verify temp files aren't needed by running applications")
    print("  • Check old files before deletion - they may be important archives")
    print("\nTo delete files, run with --cleanup followed by file paths")
    print("Example: python disk_cleanup.py ./ --cleanup /path/to/file1 /path/to/file2 --force")


if __name__ == "__main__":
    main()
