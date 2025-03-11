#!/usr/bin/env python
import sys
import sqlite_web

if __name__ == "__main__":
    db_file = "olist.sqlite"  # Default database file
    if len(sys.argv) > 1:
        db_file = sys.argv[1]  # Use first argument as database file if provided

    # Start the web interface
    sqlite_web.main([db_file, "--host=0.0.0.0", "--port=8081", "--no-browser"])
