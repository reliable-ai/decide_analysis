import os

# Base directory configuration
BASE_DIR = "/Users/ruben/Downloads/FinaleVersionUnterlagen"
LOG_DIR = os.path.join(BASE_DIR, "log")
ORIG_DIR = os.path.join(BASE_DIR, "orig", "siab_r_7517_v1_stata")
DATA_DIR = os.path.join(BASE_DIR, "data")
PROG_DIR = os.path.join(BASE_DIR, "prog Stata")

# Dataset configuration
DATE_STR = "20180706_samp"
DATANAME = "siab_r_7517_v1"
LOGNAME = "siab_7514_v1_prep"


# Ensure required directories exist
def create_directories():
    """Create all required directories if they don't exist."""
    for directory in [LOG_DIR, ORIG_DIR, DATA_DIR, PROG_DIR]:
        os.makedirs(directory, exist_ok=True)
