"""
Multiverse configuration for unemployment prediction analysis.

This file defines the multiverse analysis configuration, specifying each
judgment call and its possible choices. This includes different data cleaning
strategies, modeling approaches, and more.

Current Dimensions:
    Data Cleaning:
        - spell_gap_threshold: Days needed to split unemployment spells
        - separate_benefit_threshold: Days to separate benefit receipt periods
        - missing_strategy: Approaches for handling missing data

    Random Seeds:
        - split_seed: Seed for train/test data splitting

    Modeling:
        - model: Classification algorithm choice
        - features: Feature inclusion/exclusion strategies

Usage:
    This configuration is consumed by the `multiversum` framework to generate
    and execute all possible combinations of analytical choices, producing a
    comprehensive multiverse analysis.
"""

# imports
from multiversum import Config

# set up multiverse configuration
config = Config(
    
    # dimensions map is used to define all judgment calls
    dimensions={
        
        # ==== Data Cleaning ====
        # threshold for gap size needed to split a spell into two spells
        "spell_gap_threshold": [15, 42, 60], # days
        # threshold for gap size needed for two benefit receipts to be separated
        "separate_benefit_threshold": [5, 10, 15],  # days
        # strategies for imputing missing data
        "missing_strategy": [
            "drop_col50_drop_row",
            "drop_col50_impute_median",
            "all_impute_median",
        ],

        # ==== Random Seeds ====
        # train/test split seed
        "split_seed": list(range(3)),

        # ==== Modeling ====
        # model class
        "model": ["logistic", "logistic-ridge", "random_forest"],
        # feature selection strategy
        "features": ["all", "no_gender", "no_german"],
    },
)
