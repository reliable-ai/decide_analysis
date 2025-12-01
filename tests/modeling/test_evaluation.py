import numpy as np
from src.modeling.evaluation import evaluate_predictions


def test_evaluate_predictions_basic():
    y_true = np.array([0, 1, 1, 0, 1])
    y_pred = np.array([0, 1, 0, 0, 1])
    metrics = evaluate_predictions(y_true, y_pred)
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "confusion_matrix" in metrics


def test_evaluate_predictions_with_proba():
    y_true = np.array([0, 1, 1, 0])
    y_pred = np.array([0, 1, 1, 0])
    y_proba = np.array([0.1, 0.9, 0.8, 0.2])
    metrics = evaluate_predictions(y_true, y_pred, y_proba)
    assert "roc_auc" in metrics
