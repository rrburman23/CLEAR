import pandas as pd
import glob
import os

# 1. Use an explicit glob pattern that captures the nested structure
# This pattern matches any folder inside logs that starts with 'run_'
search_pattern = "tests/logs/run_*/dataset.csv"
files = glob.glob(search_pattern)

print(f"DEBUG: Found {len(files)} files with pattern '{search_pattern}'")

if not files:
    print("[ERROR] No files found! Check your folder paths.")
    exit(1)

all_data = []
for i, file in enumerate(files, start=1):
    try:
        df = pd.read_csv(file)
        df["run_id"] = i  # Add the run_id
        all_data.append(df)
        print(f"Successfully loaded: {file}")
    except Exception as e:
        print(f"Could not load {file}: {e}")

if all_data:
    master_df = pd.concat(all_data, ignore_index=True)
    master_df.to_csv("master_dataset.csv", index=False)
    print(
        f"Success! Master dataset saved to 'master_dataset.csv'. Total rows: {len(master_df)}"
    )
else:
    print("[ERROR] No valid CSV data could be loaded.")
