# imports
import numpy as np
import pandas as pd
from pathlib import Path
from src.metrics.metrics import (
    organize_multiverse_results,
    within_bucket_variation,
    between_bucket_variation,
)
import random

def check_order_invariance():
    
    # get all csv files in the data directory for run of interest
    data_dir = Path("output/runs/1/data")
    csv_files = list(data_dir.glob("*.csv"))
    print(f"Found {len(csv_files)} CSV files.")

    # read all files with mixed types
    arrays = []
    for i, f in enumerate(csv_files):
        arr = np.genfromtxt(f, delimiter=',', dtype=None, encoding='utf-8')
        arrays.append(arr)
        if (i + 1) % 1000 == 0:
            print(f"Loaded {i+1}/{len(csv_files)} files")

    # stack all arrays vertically
    data = np.concatenate(arrays)
    # convert data to pandas df
    df = pd.DataFrame(data)
    # remove all rows that are exact duplicates, since they are removing the rows of column names
    df = df.drop_duplicates()
    # make first row the header
    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)
    
    # create a list of 10 different shuffled dimension orders
    dimensions = [
        "spell_gap_threshold",
        "new_job_notif_threshold",
        "new_job_no_notif_threshold",
        "missing_strategy",
        "split_seed",
        "model"
    ]
    performance_metrics = ["acc", "f1", "roc_auc"]
    # prepend test_ to all performance metric names
    performance_metrics = ["test_" + metric for metric in performance_metrics]
    # make all cols that start with test_ numeric
    for col in df.columns:
        if col.startswith("test_"):
            df[col] = pd.to_numeric(df[col])
    # shuffle 10 times, save results
    within_importances = []
    between_importances = []
    for i in range(10):
        random.seed(i)
        shuffled_dims = random.sample(dimensions, len(dimensions))
        shuffled_dims = ["mv_dim_" + dim for dim in shuffled_dims]
        multi_df = organize_multiverse_results(df, shuffled_dims, performance_metrics)
        within = within_bucket_variation(multi_df, "test_acc")
        # change keys of within to be the dimension names instead of the dimension columns
        within = {shuffled_dims[i]: within[i] for i in range(len(shuffled_dims))}
        within_importances.append(within)
        between = between_bucket_variation(multi_df, "test_acc")
        between_importances.append(between)
        print(f"Completed shuffle {i+1}/10")
        
    # create a dataframe of the within importances, where the columns are the keys
    # and the values are their values over the 10 shuffles
    within_importances_df = pd.DataFrame(within_importances)
    between_importances_df = pd.DataFrame(between_importances)
    
    # write the dfs to csv
    within_importances_df.to_csv("invariance_output/within_importances.csv", index=False)
    between_importances_df.to_csv("invariance_output/between_importances.csv", index=False)

    # check if the columns all have the same values across all 10 shuffles
    within_invariant = all(within_importances_df[col].nunique() == 1 for col in within_importances_df.columns)
    between_invariant = all(between_importances_df[col].nunique() == 1 for col in between_importances_df.columns)
    print(f"Within importances are invariant to dimension order: {within_invariant}.")
    print(f"Between importances are invariant to dimension order: {between_invariant}.")
    
    return

if __name__ == "__main__":
    
    check_order_invariance()