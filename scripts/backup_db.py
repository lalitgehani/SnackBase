#!/usr/bin/env python3
"""Database backup script for SnackBase.

This script creates a timestamped backup of the SQLite database.
For PostgreSQL, it would wrap pg_dump.
"""

import shutil
import sys
from pathlib import Path
from datetime import datetime
import os

# Add src to path to import config
sys.path.append(str(Path(__file__).parent.parent / "src"))

from snackbase.core.config import get_settings

def backup_database():
    """Create a backup of the current database."""
    settings = get_settings()
    
    # Only implemented for SQLite for now
    if not settings.database_url.startswith("sqlite"):
        print(f"Backup not implemented for database type: {settings.database_url}")
        return

    # Extract path from sqlite+aiosqlite:///path/to/file.db
    db_path_str = settings.database_url.split(":///")[-1]
    db_path = Path(db_path_str)
    
    if not db_path.exists():
        print(f"Database file not found at: {db_path}")
        return

    # Create backup directory
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{db_path.stem}_{timestamp}.db"
    backup_path = backup_dir / backup_filename
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"Successfully backed up database to: {backup_path}")
        
        # Keep only last 5 backups
        backups = sorted(backup_dir.glob(f"{db_path.stem}_*.db"))
        if len(backups) > 5:
            for old_backup in backups[:-5]:
                old_backup.unlink()
                print(f"Removed old backup: {old_backup}")
                
    except Exception as e:
        print(f"Failed to backup database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    backup_database()
