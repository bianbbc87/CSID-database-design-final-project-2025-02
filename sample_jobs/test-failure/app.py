#!/usr/bin/env python3
import time
import sys

print("🚀 Starting backup job...")
print("📁 Connecting to database...")
time.sleep(2)

print("📋 Checking backup permissions...")
time.sleep(1)

print("❌ ERROR: Permission denied!")
print("💥 Failed to access backup directory: /restricted/backup")
print("🔒 User 'backup-user' does not have write permissions")

sys.exit(1)
