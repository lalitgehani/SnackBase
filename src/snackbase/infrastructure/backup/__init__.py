"""Instance-level backup and restore subsystem.

This package is deliberately independent of ``snackbase.infrastructure.storage``:
user file uploads and backup archives are separate subsystems with separate
constraints. Archives are multi-gigabyte, so nothing here may buffer a whole
archive in memory or apply upload-size/mime limits.
"""
