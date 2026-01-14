import pandas as pd
import numpy as np

from typing import Any, Dict


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


def _resolve_targets(df: pd.DataFrame, action_dict: Dict[str, Any]) -> list[str]:
    """
    Resolve column targets from action dictionary to a list of column names.

    Args:
        df: Input DataFrame
        action_dict: Action dictionary containing either:
            - {"columns": ["col1", "col2"]}: List of column names
            - {"column_type": "numeric"}: Column type ("numeric", "categorical", "datetime", "boolean")

    Returns:
        List of column names matching the specification
    """
    if "columns" in action_dict:
        columns = action_dict["columns"]
        if isinstance(columns, list):
            # Validate that all columns exist
            missing_cols = [col for col in columns if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Columns not found in DataFrame: {missing_cols}")
            return columns
        else:
            raise ValueError("'columns' must be a list of column names")
    elif "column_type" in action_dict:
        col_type = action_dict["column_type"]
        if col_type == "numeric":
            return df.select_dtypes(include=[np.number]).columns.tolist()
        elif col_type == "categorical":
            return df.select_dtypes(include=["object", "category"]).columns.tolist()
        elif col_type == "datetime":
            return df.select_dtypes(include=["datetime64"]).columns.tolist()
        elif col_type == "boolean":
            return df.select_dtypes(include=["bool"]).columns.tolist()
        else:
            raise ValueError(
                f"Unknown column_type: '{col_type}'. Supported types: "
                "'numeric', 'categorical', 'datetime', 'boolean'"
            )
    else:
        raise ValueError("Action must contain either 'columns' or 'column_type'")


def _impute_column(df: pd.DataFrame, col: str, method: Any) -> None:
    """
    Impute missing values in a single column in-place.

    Args:
        df: Input DataFrame (modified in-place)
        col: Column name to impute
        method: Imputation method ("mean", "median", "mode", "zero", or numeric value)
    """
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not found in DataFrame")

    if method == "mean":
        df[col] = df[col].fillna(df[col].mean())
    elif method == "median":
        df[col] = df[col].fillna(df[col].median())
    elif method == "mode":
        mode_value = df[col].mode()
        if len(mode_value) > 0:
            df[col] = df[col].fillna(mode_value.iloc[0])
        else:
            raise ValueError(
                f"Cannot compute mode for column '{col}' because all values are missing"
            )
    elif method == "zero":
        df[col] = df[col].fillna(0)
    elif isinstance(method, (int, float)):
        df[col] = df[col].fillna(method)
    else:
        raise ValueError(
            f"Unknown imputation method '{method}' for column '{col}'. "
            "Supported methods: 'mean', 'median', 'mode', 'zero', or a numeric value"
        )


def handle_missing_values(df: pd.DataFrame, strategy: list[Dict[str, Any]]) -> pd.DataFrame:
    """
    Handle missing values in the DataFrame by applying specific rules.

    Args:
        df: Input DataFrame
        strategy: List of dictionaries, where each dictionary specifies an
            action. The actions are applied sequentially in the order they are
            specified. Each dictionary must have an "action" key and additional
            parameters depending on the action type.

            Supported actions:

            1. drop_columns: Drop columns based on missing value threshold or by selection
               - With threshold: {"action": "drop_columns", "threshold": 0.6}
                 Drops columns with >60% missing values
               - By name: {"action": "drop_columns", "columns": ["col1", "col2"]}
                 Drops specific columns by name
               - By type: {"action": "drop_columns", "column_type": "numeric"}
                 Drops all numeric columns

            2. drop_rows: Drop rows with missing values in specified columns
               - By name: {"action": "drop_rows", "columns": ["col1", "col2"]}
                 Drops rows with missing values in specified columns
               - By type: {"action": "drop_rows", "column_type": "numeric"}
                 Drops rows with missing values in any numeric column

            3. impute: Impute missing values with various strategies
               - By column list:
                 {"action": "impute", "method": "mean", "columns": ["col1", "col2"]}
               - By column type:
                 {"action": "impute", "method": "mean", "column_type": "numeric"}

            Supported imputation methods: "mean", "median", "mode", "zero", or numeric value
            Supported column types: "numeric", "categorical", "datetime", "boolean"

    Returns:
        DataFrame with missing values handled according to the strategy
    """

    df = df.copy()  # work on a copy to avoid modifying the original

    # loop through each action in the strategy. this should apply them in order.
    for action_dict in strategy:
        if not isinstance(action_dict, dict):
            raise ValueError(f"Each strategy item must be a dictionary. Got: {action_dict}")

        if "action" not in action_dict:
            raise ValueError(
                f"Each strategy item must have an 'action' key. Got: {action_dict}"
            )

        action = action_dict["action"]

        if action == "drop_columns":
            # drop columns with missing value percentage above threshold OR by column selection
            if "threshold" in action_dict:
                threshold = action_dict["threshold"]
                if not isinstance(threshold, (int, float)) or not (0 <= threshold <= 1):
                    raise ValueError(
                        f"'threshold' must be a float between 0 and 1. Got: {threshold}"
                    )
                missing_pct = df.isnull().sum() / len(df)
                cols_to_drop = missing_pct[missing_pct > threshold].index.tolist()
                df = df.drop(columns=cols_to_drop)
            elif "columns" in action_dict or "column_type" in action_dict:
                cols_to_drop = _resolve_targets(df, action_dict)
                df = df.drop(columns=cols_to_drop)
            else:
                raise ValueError(
                    "'drop_columns' action requires either 'threshold', 'columns', or 'column_type'"
                )

        elif action == "drop_rows":
            # drop rows with missing values in specified columns
            if "columns" not in action_dict and "column_type" not in action_dict:
                raise ValueError("'drop_rows' action requires either 'columns' or 'column_type'")

            cols = _resolve_targets(df, action_dict)
            df = df.dropna(axis=0, subset=cols)

        elif action == "impute":
            # impute missing values with specified method
            if "columns" not in action_dict and "column_type" not in action_dict:
                raise ValueError("'impute' action requires either 'columns' or 'column_type'")

            if "method" not in action_dict:
                raise ValueError("'impute' action requires 'method'")

            method = action_dict["method"]
            cols = _resolve_targets(df, action_dict)
            for col in cols:
                _impute_column(df, col, method)
        else:
            raise ValueError(
                f"Unknown action: '{action}'. Supported actions: 'drop_columns', 'drop_rows', 'impute'"
            )

    return df
