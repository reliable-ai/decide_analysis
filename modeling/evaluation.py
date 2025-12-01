"""
Model Evaluation Functions

This module contains functions for evaluating machine learning model performance.
"""

from sklearn.metrics import confusion_matrix, roc_auc_score, accuracy_score


def evaluate_predictions(y_true, y_pred, y_pred_proba=None):
    """
    Evaluates predictions against ground truth.

    Args:
        y_true: Ground truth target values
        y_pred: Predicted target values (class labels)
        y_pred_proba: Predicted probabilities for positive class (optional)

    Returns:
        dict: Dictionary containing evaluation metrics
    """
    # Calculate metrics
    accuracy = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)

    # Calculate overall precision, recall, F1 from confusion matrix
    # For binary classification: use positive class (usually 1)
    tn, fp, fn, tp = cm.ravel()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    # Print evaluation
    print("=" * 60)
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-Score:  {f1:.4f}")

    print("\nConfusion Matrix:")
    print(cm)

    # Calculate ROC-AUC if probabilities provided
    roc_auc = None
    if y_pred_proba is not None:
        roc_auc = roc_auc_score(y_true, y_pred_proba)
        print(f"\nROC-AUC Score: {roc_auc:.4f}")

    print("=" * 60)

    # Return metrics as dictionary
    metrics = {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "confusion_matrix": cm,
        "predictions": y_pred,
    }

    if roc_auc is not None:
        metrics["roc_auc"] = roc_auc

    return metrics
