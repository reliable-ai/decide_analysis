import sys
import pandas as pd
from multiversum import Universe
from sklearn.linear_model import LogisticRegression
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


settings = {
    # Configuration of this universe
    # (automatically overriden when running the multiverse analysis)
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


universe = Universe(
    settings=settings,
    # Set a global seed for reproducibility
    seed=42,
)

# Get the parsed universe dimensions
dimensions = universe.dimensions


pd.set_option("display.max_columns", None)


df = read_data(50000)
df.head(10)


df = translate_to_english(df)
df.head(10)


df = fix_data_types(df)
df.head(10)


df = identify_unemployment_episodes(
    df,
    spell_gap_threshold=dimensions["spell_gap_threshold"],
)
df.head(10)


df = generate_biographical_variables(
    df,
    new_job_no_notif_threshold=dimensions["new_job_no_notif_threshold"],
    new_job_notif_threshold=dimensions["new_job_notif_threshold"],
    separate_benefit_threshold=dimensions["separate_benefit_threshold"],
)
df.head(10)


year_range = list(range(dimensions["year_range_start"], dimensions["year_range_end"] + 1))
year_range


df = index_unemployment_entries(
    df,
    year_range=year_range,
)
df.head(10)


df = generate_employment_history(df, 1)
df.head(10)


df = reshape_data_for_ml(df)
df.head(10)


# First, replace placeholder values (99999) with proper NaN
df = replace_missing_value_placeholder(df, placeholder=99999)

# Apply missing value strategy based on dimension configuration
missing_strategy = dimensions["missing_strategy"]

if missing_strategy == "drop_60_impute_median":
    # Drop columns with >60% missing, then impute remaining with median
    strategy = [
        {"action": "drop_columns", "threshold": 0.6},
        {"action": "impute", "method": "median", "column_type": "numeric"},
        {"action": "impute", "method": "fixed", "column_type": "categorical"},
    ]

elif missing_strategy == "drop_80_impute_median":
    # Drop extremely sparse columns (>80%)
    strategy = [
        {"action": "drop_columns", "threshold": 0.8},
        {"action": "impute", "method": "median", "column_type": "numeric"},
        {"action": "impute", "method": "fixed", "column_type": "categorical"},
    ]

elif missing_strategy == "all_impute_median":
    # Keep all columns, impute all numeric
    strategy = [
        {"action": "impute", "method": "median", "column_type": "numeric"},
        {"action": "impute", "method": "fixed", "column_type": "categorical"},
        {"action": "drop_columns", "threshold": 0.01},  # Drop any remaining columns
    ]

elif missing_strategy == "zero_imputation":
    # Replace all missing with zero
    strategy = [
        {"action": "impute", "method": "fixed", "column_type": "numeric", "value": 0},
        {"action": "impute", "method": "fixed", "column_type": "categorical"},
    ]

else:
    raise ValueError(f"Unknown missing strategy: {missing_strategy}")

# Apply the selected strategy
df = handle_missing_values(df, strategy, verbose=True)

print(f"Shape after missing value handling: {df.shape}")
print(f"Remaining missing values: {df.isnull().sum().sum()}")
df.head()

# Assert no missing values remain
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
    raise ValueError(f"Unknown feature selection strategy: {dimensions['features']}")


X = select_features(
    df,
    features=features,
    additional_exclude=additional_exclude
)
X.head(10)


X.shape


X.columns.to_list()


y = select_target(df)
y.head(10)


print(f"Feature Shape: {X.shape}")
print(f"Target Shape: {y.shape}")
print(f"Target distribution (full): {y.value_counts(normalize=True)}")


split_stratify: bool
split_chronological: bool

if dimensions["split_strategy"] == "random":
    split_stratify = False
    split_chronological = False
elif dimensions["split_strategy"] == "stratified":
    split_stratify = True
    split_chronological = False
elif dimensions["split_strategy"] == "chronological":
    split_stratify = False
    split_chronological = True
elif dimensions["split_strategy"] == "stratified-chronological":
    split_stratify = True
    split_chronological = True
else:
    raise ValueError(f"Unknown split strategy: {dimensions['split_strategy']}")

X_train, X_test, y_train, y_test = split_data(
    X,
    y,
    stratify=split_stratify,
    chronological=split_chronological,
    random_state=dimensions["split_seed"]
)


print(f"Training set size: {X_train.shape}")
print(f"Test set size: {X_test.shape}")
print(f"Target distribution (train): {y_train.value_counts(normalize=True)}")


model: LogisticRegression | RandomForestClassifier

if dimensions["model"] == "logistic":
    model = LogisticRegression(
        max_iter=1000,
        random_state=dimensions["model_seed"],
        class_weight="balanced",
        solver="lbfgs",
    )
elif dimensions["model"] == "random_forest":
    model = RandomForestClassifier(
        random_state=dimensions["model_seed"],
        class_weight="balanced",
    )
else:
    raise ValueError(f"Unknown model type: {dimensions['model']}")


print("Training model...")
model.fit(X_train, y_train)
print("Model trained successfully!")

print(f"\nTraining Accuracy: {model.score(X_train, y_train):.4f}")
print(f"Test Accuracy: {model.score(X_test, y_test):.4f}")


# Extract coefficients or feature importances
if dimensions["model"] == "logistic":
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


# Make predictions
y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)

# Get prediction probabilities
y_pred_proba_train = model.predict_proba(X_train)[:, 1]
y_pred_proba_test = model.predict_proba(X_test)[:, 1]


# Evaluate on training set
print("TRAINING SET")
train_results = evaluate_predictions(y_train, y_pred_train, y_pred_proba_train)


# Evaluate on test set
print("TEST SET")
test_results = evaluate_predictions(y_test, y_pred_test, y_pred_proba_test)


final_data = pd.DataFrame(
    {
        "perf_acc": test_results["accuracy"],
        "perf_precision": test_results["precision"],
        "perf_recall": test_results["recall"],
        "perf_f1": test_results["f1_score"],
        "perf_roc_auc": test_results["roc_auc"],

        # Add model coefficients / var. importance
        **coef_dict,
    },
    index=[universe.universe_id],
)
final_data


universe.save_data(final_data)


df_pred = pd.DataFrame({
    "id": y_test.index,
    "y_pred": y_pred_test,
    "y_pred_proba": y_pred_proba_test
})
df_pred.head()


universe.export_dataframe(df_pred, "y_pred_test.parquet")
