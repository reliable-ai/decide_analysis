# imports
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

if __name__ == "__main__":

    # get all csv files in the data directory for run of interest
    data_dir = Path("output/runs/2/data")
    csv_files = list(data_dir.glob("*.csv"))
    print(f"Found {len(csv_files)} CSV files.")

    # check file sizes first
    total_size_mb = sum(f.stat().st_size for f in csv_files) / 1024 / 1024
    print(f"Total size: {total_size_mb:.2f} MB")

    # read in smaller batches
    batch_size = 10
    dfs = []
    for i in range(0, len(csv_files), batch_size):
        batch = csv_files[i:i+batch_size]
        batch_df = pd.concat([pd.read_csv(f) for f in batch], ignore_index=True)
        dfs.append(batch_df)
        print(f"Processed {i+len(batch)}/{len(csv_files)} files")

    # concatenate all batches into a single df
    df = pd.concat(dfs, ignore_index=True)

    # write the df to pcs_multiverse/analyze_output.csv
    output_path = Path("pcs_multiverse/analyze_output.csv")
    df.to_csv(output_path, index=False)