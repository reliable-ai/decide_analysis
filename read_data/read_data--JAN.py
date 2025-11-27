import pandas as pd

def read_data(nrows: int | None = None) -> pd.DataFrame:
    # Read from temporarily decrypted file
    path = "../siab-data/siab_r_7521_v1.dta"

    if nrows is not None:
        with pd.read_stata(path, chunksize=nrows, convert_categoricals=True) as itr:
            # Read only the first chunk
            df = next(itr)
    else:
        # Read full file
        df = pd.read_stata(path, convert_categoricals=True)
    return df
