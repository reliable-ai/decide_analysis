import sys
import pandas as pd
from multiversum import Universe
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.ensemble import RandomForestClassifier
from pathlib import Path
# add project root to sys.path so 'src' can be imported
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from src.read_data.read_data import read_data  # noqa: E402
from src.read_data.translate_names import translate_to_english  # noqa: E402
from src.read_data.fix_types import fix_data_types  # noqa: E402
from src.data_cleaning.feature_engineering import (  # noqa: E402
    identify_unemployment_episodes,
    generate_biographical_variables,
    index_unemployment_entries,
    generate_employment_history,
)
from src.data_cleaning.transform import reshape_data_for_ml  # noqa: E402
from src.data_cleaning.missing_values import (  # noqa: E402
    replace_missing_value_placeholder,
    handle_missing_values,
)
from src.modeling.setup import select_features, select_target  # noqa: E402
from src.modeling.data_split import split_data  # noqa: E402
from src.modeling.evaluation import evaluate_predictions  # noqa: E402

# this mapping defines the configuration of this universe.
# it is automatically overridden when running the multiverse analysis.
settings = {
    
    # same as in multiverse.py, except only a single choice per dimension
    "dimensions": {
        # ==== Data Cleaning ====
        "spell_gap_threshold": 42,
        "new_job_notif_threshold": 92,
        "new_job_no_notif_threshold": 366,
        "separate_benefit_threshold": 10,
        "year_range_start": 2010,
        "year_range_end": 2013,
        "missing_strategy": "all_impute_median",

        # ==== Random Seeds ====
        "split_seed": 80539,
        "model_seed": 54,

        # ==== Modeling ====
        "split_strategy": "random",
        "model": "random_forest",
        "features": "all",
    }
}

# initialize the universe with the given settings
universe = Universe(
    settings=settings, # seed handled by multiversum
)

# get the parsed universe dimensions
dimensions = universe.dimensions

# ===== DATA ANALYSIS PIPELINE =====
df = read_data(50000)
df = translate_to_english(df)
df = fix_data_types(df)
df = identify_unemployment_episodes(
    df,
    spell_gap_threshold=dimensions["spell_gap_threshold"],
)
df = generate_biographical_variables(
    df,
    separate_benefit_threshold=dimensions["separate_benefit_threshold"],
)
df = index_unemployment_entries(df)
df = generate_employment_history(df, 1)
df = reshape_data_for_ml(df)
# first, replace placeholder values (99999) with proper NaN
df = replace_missing_value_placeholder(df, placeholder=99999)
# apply missing value strategy based on dimension configuration
missing_strategy = dimensions["missing_strategy"]
if missing_strategy == "drop_col50_drop_row":
    # drop columns with >50% missing, then drop rows with any missing
    strategy = [
        {"action": "drop_columns", "threshold": 0.5},
        {"action": "drop_rows", "column_type": "all"},
    ]
elif missing_strategy == "drop_col50_impute_median":
    # drop columns with >50% missing, then impute
    strategy = [
        {"action": "drop_columns", "threshold": 0.5},
        {"action": "impute", "method": "median", "column_type": "numeric"},
        {"action": "impute", "method": "fixed", "column_type": "categorical"},
    ]
elif missing_strategy == "all_impute_median":
    # keep all columns, impute all numeric
    strategy = [
        {"action": "impute", "method": "median", "column_type": "numeric"},
        {"action": "impute", "method": "fixed", "column_type": "categorical"},
        {"action": "impute", "method": "fixed", "column_type": "boolean", "value": False},
        {"action": "drop_columns", "threshold": 0.001},  # drop any remaining NAs
    ]
elif missing_strategy == "zero_imputation":
    # replace all missing with zero
    strategy = [
        {"action": "impute", "method": "fixed",
         "column_type": "numeric", "value": 0},
        {"action": "impute", "method": "fixed", "column_type": "categorical"},
        {"action": "impute", "method": "fixed", "column_type": "boolean", "value": False},
    ]
else:
    raise ValueError(f"Unknown missing strategy: {missing_strategy}")

# apply the selected strategy
df = handle_missing_values(df, strategy, verbose=True)

# assert no missing values remain
assert df.isnull().sum().sum() == 0

features = None # i.e. all non-excluded
additional_exclude = None

if dimensions["features"] == "all":
    pass
elif dimensions["features"] == "no_gender":
    # TODO: CHECK COLNAMES
    additional_exclude = ["frau1"]
elif dimensions["features"] == "no_german":
    # TODO: CHECK COLNAMES
    additional_exclude = ["maxdeutsch"]
elif dimensions["features"] == "no_gender-german":
    # TODO: CHECK COLNAMES
    additional_exclude = ["frau1", "maxdeutsch"]
else:
    raise ValueError(f"Unknown feature strategy: {dimensions['features']}.")

# perform ML part
X = select_features(
    df,
    features=features,
    additional_exclude=additional_exclude
)
y = select_target(df)
X_train, X_test, y_train, y_test = split_data(
    X,
    y,
    random_state=dimensions["split_seed"]
)

model: LogisticRegression | LogisticRegressionCV | RandomForestClassifier

if dimensions["model"] == "logistic":
    model = LogisticRegression(
        max_iter=1000,
        random_state=42,
        class_weight="balanced",
        solver="lbfgs",
    )
elif dimensions["model"] == "logistic-ridge":
    model = LogisticRegressionCV(
        cv=5,
        penalty="l2",
        solver="lbfgs",
        max_iter=1000,
        random_state=42,
        class_weight="balanced",
        tol=1e-3,
    )
elif dimensions["model"] == "random_forest":
    model = RandomForestClassifier(
        random_state=42,
        class_weight="balanced",
    )
else:
    raise ValueError(f"Unknown model type: {dimensions['model']}")

model.fit(X_train, y_train)

# extract coefficients or feature importances
if dimensions["model"] in ["logistic", "logistic-ridge"]:
    # For logistic regression, get coefficients
    coefficients = model.coef_[0]  # Shape: (n_features,)
    coef_dict = {f"coef_{col}": coef for col, coef in zip(model.feature_names_in_, coefficients)}
elif dimensions["model"] == "random_forest":
    # For random forest, get feature importances
    importances = model.feature_importances_
    coef_dict = {f"varimp_{col}": imp for col, imp in zip(model.feature_names_in_, importances)}
else:
    raise ValueError("Model type not supported for coefficient/importance extraction")

print(f"Extracted {len(coef_dict)} coefficient/importance values")


# make predictions
y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)

# get prediction probabilities
y_pred_proba_train = model.predict_proba(X_train)[:, 1]
y_pred_proba_test = model.predict_proba(X_test)[:, 1]

# evaluate on training set
train_results = evaluate_predictions(y_train, y_pred_train, y_pred_proba_train)

# evaluate on test set
test_results = evaluate_predictions(y_test, y_pred_test, y_pred_proba_test)

final_data = pd.DataFrame(
    {
        "test_acc": test_results["accuracy"],
        "test_precision": test_results["precision"],
        "test_recall": test_results["recall"],
        "test_f1": test_results["f1_score"],
        "test_roc_auc": test_results["roc_auc"],
        # add model coefficients / var. importance
        **coef_dict,
    },
    index=[universe.universe_id],
)

universe.save_data(final_data)

df_pred = pd.DataFrame({
    "id": y_test.index,
    "y_pred": y_pred_test,
    "y_pred_proba": y_pred_proba_test
})

universe.export_dataframe(df_pred, "y_pred_test.parquet")
