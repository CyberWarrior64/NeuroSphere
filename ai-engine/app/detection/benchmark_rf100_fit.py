from pathlib import Path
import time

import numpy as np
from sklearn.ensemble import RandomForestClassifier

base = Path(__file__).resolve().parents[2]
data = base / "datasets" / "processed" / "hybrid_v2_training"
X = np.load(data / "X_train.npy")
y = np.load(data / "y_train.npy")
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=25,
    min_samples_leaf=2,
    class_weight="balanced",
    n_jobs=-1,
    random_state=42,
    verbose=0,
)
start = time.perf_counter()
model.fit(X, y)
print(f"SAME_CONFIG_100_TREE_FIT_SECONDS={time.perf_counter() - start:.3f}")
