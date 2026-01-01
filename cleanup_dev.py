#!/usr/bin/env python3
"""Development cleanup script for SnackBase.

This script removes:
- All uploaded files in sb_data/files/
- All dynamic migrations in sb_data/migrations/
- The SQLite database file (snackbase.db)

WARNING: This will delete all data! Only use in development.
"""

import argparse
import shutil
import sys
from pathlib import Path


def confirm_cleanup(skip_confirm: bool = False) -> bool:
    """Ask user to confirm the cleanup operation.
    
    Args:
        skip_confirm: If True, skip the confirmation prompt and return True.
    
    Returns:
        True if user confirms or skip_confirm is True, False otherwise.
    """
    if skip_confirm:
        return True
    
    print("⚠️  WARNING: This will delete ALL development data!")
    print("\nThe following will be removed:")
    print("  - All uploaded files (sb_data/files/)")
    print("  - All dynamic migrations (sb_data/migrations/)")
    print("  - Database files (sb_data/snackbase.db + WAL/SHM)")
    print("  - Security test reports (tests/security-reports/)")
    print("\nThis action cannot be undone!")

    
    response = input("\nAre you sure you want to continue? (yes/no): ").strip().lower()
    return response in ['yes', 'y']


def cleanup_directory(path: Path, description: str) -> None:
    """Remove a directory and all its contents."""
    if path.exists():
        try:
            shutil.rmtree(path)
            print(f"✅ Removed {description}: {path}")
        except Exception as e:
            print(f"❌ Failed to remove {description}: {e}")
    else:
        print(f"ℹ️  {description} does not exist: {path}")


def cleanup_file(path: Path, description: str) -> None:
    """Remove a single file."""
    if path.exists():
        try:
            path.unlink()
            print(f"✅ Removed {description}: {path}")
        except Exception as e:
            print(f"❌ Failed to remove {description}: {e}")
    else:
        print(f"ℹ️  {description} does not exist: {path}")


def main():
    """Main cleanup function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Clean up SnackBase development environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup_dev.py          # Interactive mode with confirmation
  python cleanup_dev.py -y       # Skip confirmation prompt
  uv run cleanup_dev.py -y       # Skip confirmation with uv
        """
    )
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Skip confirmation prompt and proceed with cleanup'
    )
    
    args = parser.parse_args()
    
    # Get project root (script is in project root)
    project_root = Path(__file__).parent
    
    # Define paths to clean
    files_dir = project_root / "sb_data" / "files"
    migrations_dir = project_root / "sb_data" / "migrations"
    db_file = project_root / "sb_data" / "snackbase.db"
    db_wal_file = project_root / "sb_data" / "snackbase.db-wal"
    db_shm_file = project_root / "sb_data" / "snackbase.db-shm"
    security_reports_dir = project_root / "tests" / "security-reports"
    
    print("=" * 60)
    print("SnackBase Development Cleanup Script")
    print("=" * 60)
    print()
    
    # Confirm with user (skip if -y flag is provided)
    if not confirm_cleanup(skip_confirm=args.yes):
        print("\n❌ Cleanup cancelled.")
        sys.exit(0)
    
    print("\n" + "=" * 60)
    print("Starting cleanup...")
    print("=" * 60)
    print()
    
    # Clean uploaded files
    cleanup_directory(files_dir, "Uploaded files directory")
    
    # Clean dynamic migrations
    cleanup_directory(migrations_dir, "Dynamic migrations directory")
    
    # Clean database files (main DB + WAL + SHM)
    cleanup_file(db_file, "Database file")
    cleanup_file(db_wal_file, "Database WAL file")
    cleanup_file(db_shm_file, "Database SHM file")
    
    # Clean security reports
    cleanup_directory(security_reports_dir, "Security test reports directory")
    
    print()
    print("=" * 60)
    print("✨ Cleanup complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Restart the server: uv run snackbase serve")
    print("  2. The database will be recreated with core migrations")
    print("  3. You'll have a fresh development environment")
    print()


if __name__ == "__main__":
    main()

