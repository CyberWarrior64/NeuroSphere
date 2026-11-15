
from pathlib import Path
import time
import joblib
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "datasets" / "processed" / "training"
MODEL_DIR = BASE_DIR / "saved_models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("NEUROSPHERE - RANDOM FOREST TRAINING")
print("=" * 65)

print("\nLoading prepared training data...")

X_train = np.load(DATA_DIR / "X_train.npy")
X_test = np.load(DATA_DIR / "X_test.npy")
y_train = np.load(DATA_DIR / "y_train.npy")
y_test = np.load(DATA_DIR / "y_test.npy")

print("Training shape:", X_train.shape)
print("Testing shape:", X_test.shape)

print("\nInitializing Random Forest...")

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=25,
    min_samples_leaf=2,
    class_weight="balanced",
    n_jobs=-1,
    random_state=42,
    verbose=1
)

print("\nTraining started...")
start_time = time.time()

model.fit(X_train, y_train)

training_time = time.time() - start_time

print(f"\nTraining completed in {training_time:.2f} seconds.")

print("\nEvaluating model...")

y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, zero_division=0)
recall = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)
roc_auc = roc_auc_score(y_test, y_prob)

tn, fp, fn, tp = confusion_matrix(
    y_test, y_pred, labels=[0, 1]
).ravel()

fpr = fp / (fp + tn) if (fp + tn) else 0

print("\n" + "=" * 65)
print("NEUROSPHERE - MODEL PERFORMANCE")
print("=" * 65)

print(f"Accuracy       : {accuracy:.4f} ({accuracy * 100:.2f}%)")
print(f"Precision      : {precision:.4f}")
print(f"Recall         : {recall:.4f}")
print(f"F1 Score       : {f1:.4f}")
print(f"ROC-AUC        : {roc_auc:.4f}")
print(f"False Positive : {fpr:.4f} ({fpr * 100:.2f}%)")

print("\nConfusion Matrix:")
print(f"True Negatives : {tn}")
print(f"False Positives: {fp}")
print(f"False Negatives: {fn}")
print(f"True Positives : {tp}")

print("\nClassification Report:")
print(classification_report(
    y_test,
    y_pred,
    target_names=["NORMAL", "ATTACK"],
    zero_division=0
))

model_path = MODEL_DIR / "random_forest_cicids2017.joblib"
joblib.dump(model, model_path, compress=3)

print("Model saved to:", model_path)
print("\nRandom Forest training completed successfully.")
