from multiversum import Config

# Configure the multiverse itself
config = Config(
    # Specify the decisions / dimensions and their options
    dimensions={
        # ==== Data Cleaning ====
        # Threshold for gap size needed to split a spell into two spells
        "spell_gap_threshold": [42, 30, 60], # days
        # Threshold for gap size needed to count a job as "new"
        "new_job_notif_threshold": [92],  # days; with notification
        "new_job_no_notif_threshold": [366],  # days; without notification
        # Threshold for gap size needed for two benefit receipts to be separated.
        "separate_benefit_threshold": [10, 7, 14],  # days

        # Cutoffs for year range to be included in data
        "year_range_start": [2010],  # start year
        "year_range_end": [2013, 2014, 2015, 2016],  # end year (inclusive)

        # Strategies for imputing missing data
        "missing_strategy": [
            "drop_60_impute_median",
            "drop_80_impute_median",
            "all_impute_median",
            "zero_imputation"
        ],

        # ==== Random Seeds ====
        # Train/test split seed
        "split_seed": [80539, 94720],
        # Model seed
        "model_seed": [54, 74],

        # ==== Modeling ====
        # Train/test split rule
        # "split_strategy": ["random", "stratified", "chronological", "stratified-chronological"],
        "split_strategy": ["random", "stratified"],
        # Model class
        "model": ["logistic", "random_forest"],
        # Feature selection strategy
        "features": ["all", "no_gender", "no_german", "no_gender-german"],
    },
)
