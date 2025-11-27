import pandas as pd

def read_data(nrows: int | None = None) -> pd.DataFrame:
    # Read from temporarily decrypted file
    path = "../siab-data/siab_r_7521_v1.csv.gz"
    df = pd.read_csv(path, nrows=nrows)

    return df
