import pandas as pd
import numpy as np


def replace_missing_value_placeholder(
    df: pd.DataFrame, placeholder: int = 99999
) -> pd.DataFrame:
    """
    Replace all instances of a placeholder value (e.g., 99999) with NaN.

    Args:
        df: Input DataFrame
        placeholder: The placeholder value to replace (default: 99999)

    Returns:
        DataFrame with placeholder values replaced by NaN
    """

    return df.replace(placeholder, np.nan)


# TODO: still lots to improve on here. ideally, this function would be able to
# work somewhat like a pipeline, where we can apply a series of transformations
# to the data, and then return the transformed DataFrame. This is because this
# would follow how I often clean data in practice -> first remove some columns
# with lots of missingness, then drop some rows that still have missingness in
# certain columns, and then impute the remaining missingness with whatever makes
# sense for that particular feature.
def handle_missing_values(df: pd.DataFrame, strategy: list[str]) -> pd.DataFrame:
    """
    Handle missing values in the DataFrame by applying specific rules.

    Args:
        df: Input DataFrame
        strategy: List of dictionaries, where each dictionary specifies an
            action. The actions are applied sequentially in the order they are
            specified. Supported actions are:
            - {"drop_columns": float}: Drop columns with missing value
              percentage greater than the threshold (0.0 to 1.0). For example,
              {"drop_columns": 0.6} drops columns with >60% missing values.
            - {"drop_rows": list[str]}: Drop rows that have missing values in
              any of the specified columns. For example, {"drop_rows": ["col1",
              "col4"]} drops rows that have missing values in columns
              "col1" or "col4".
            - {"impute": dict}: Impute missing values with different strategies
              per column. The dictionary maps column names to imputation
              methods. Supported methods are: "mean", "median", "mode", "zero",
              or a numeric value. For example, {"impute": {"col1": "mean",
              "col2": "median", "col3": 0}} imputes missing values in columns
              "col1" with the mean, "col2" with the median, and "col3" with 0.
    """

    df = df.copy()  # work on a copy to avoid modifying the original

    # loop through each action in the strategy. this should apply them in order.
    for action in strategy:
        if not isinstance(action, dict) or len(action) != 1:
            raise ValueError(
                f"Each action must be a dictionary with exactly one key. Got: {action}"
            )

        action_type = list(action.keys())[0]
        action_value = action[action_type]

        if action_type == "drop_columns":
            # drop columns with missing value percentage above threshold
            if not isinstance(action_value, (int, float)) or not (
                0 <= action_value <= 1
            ):
                raise ValueError(
                    f"`drop_columns` threshold must be a float between 0 and 1. Got: {action_value}"
                )

            missing_pct = df.isnull().sum() / len(df)
            cols_to_drop = missing_pct[missing_pct > action_value].index.tolist()
            df = df.drop(columns=cols_to_drop)

        elif action_type == "drop_rows":
            # drop rows with missing values in specified columns
            if not isinstance(action_value, list):
                raise ValueError(
                    f"`drop_rows` must be a list of column names. Got: {action_value}"
                )

            # validate that all specified columns exist
            missing_cols = [col for col in action_value if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Columns not found in DataFrame: {missing_cols}")

            # drop rows that have missing values in any of the specified columns
            df = df.dropna(axis=0, subset=action_value)

        elif action_type == "impute":
            # impute missing values with different strategies per column
            if not isinstance(action_value, dict):
                raise ValueError(
                    f"`impute` must be a dictionary mapping \
                    column names to imputation methods. Got: {action_value}"
                )

            for col, method in action_value.items():
                if col not in df.columns:
                    raise ValueError(f"Column '{col}' not found in DataFrame")

                if method == "mean":
                    df[col] = df[col].fillna(df[col].mean())
                elif method == "median":
                    df[col] = df[col].fillna(df[col].median())
                elif method == "mode":
                    # for `mode`, use the most frequent value. if multiple modes
                    # exist, use the first one. this should be helpful for when
                    # we have categorical data with many missing values.
                    mode_value = df[col].mode()
                    if len(mode_value) > 0:
                        df[col] = df[col].fillna(mode_value.iloc[0])
                    else:
                        raise ValueError(
                            f"Cannot compute mode for column \
                            '{col}' because all values are missing"
                        )
                elif method == "zero":
                    df[col] = df[col].fillna(0)
                elif isinstance(method, (int, float)):
                    # fill with a specific numeric value
                    df[col] = df[col].fillna(method)
                else:
                    raise ValueError(
                        f"Unknown imputation method '{method}' \
                        for column '{col}'. Supported methods: 'mean', \
                            'median', 'mode', 'zero', or a numeric value"
                    )
        else:
            raise ValueError(
                f"Unknown action type: '{action_type}'. Supported \
                actions: 'drop_columns', 'drop_rows', 'impute'"
            )

    return df
