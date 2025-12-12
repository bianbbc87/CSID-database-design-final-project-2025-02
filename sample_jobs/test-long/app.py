#!/usr/bin/env python3
import time

print("🚀 Starting long ETL job...")
print("📊 This job will run for 30 seconds...")

for i in range(30):
    progress = (i + 1) / 30 * 100
    print(f"⏳ Progress: {progress:.1f}% ({i+1}/30 seconds)")
    time.sleep(1)

print("✅ Long job completed successfully!")
print("📈 ETL process finished")
