
import numpy as np
import joblib

from pathlib import Path
from sklearn.ensemble import IsolationForest


# NeuroSphere network traffic feature definitions
FEATURE_COLUMNS = [
    "duration_seconds",
    "source_bytes",
    "destination_bytes",
    "packet_count",
    "failed_connections",
    "connections_per_minute"
]


def generate_demo_normal_traffic(samples=2000):
    """
    Generate demonstration normal network traffic.
    This is synthetic data, not real captured traffic.
    """

    rng = np.random.default_rng(42)

    data = np.column_stack([
        rng.exponential(2, samples),       # Duration
        rng.lognormal(8, 1, samples),      # Source bytes
        rng.lognormal(8, 1, samples),      # Destination bytes
        rng.poisson(20, samples),          # Packet count
        rng.poisson(0.2, samples),         # Failed connections
        rng.normal(15, 5, samples).clip(0) # Connection rate
    ])

    return data


def train_model():
    print("Training NeuroSphere Isolation Forest...")

    training_data = generate_demo_normal_traffic()

    model = IsolationForest(
        n_estimators=200,
        contamination=0.03,
        random_state=42
    )

    model.fit(training_data)

    project_root = Path(__file__).resolve().parents[2]
    model_directory = project_root / "saved_models"
    model_directory.mkdir(exist_ok=True)

    model_path = model_directory / "isolation_forest.joblib"

    joblib.dump(model, model_path)

    print("Training completed!")
    print(f"Model saved at: {model_path}")

    return model


def detect_threat(model, traffic):
    """
    Predict whether network traffic is normal or anomalous.
    """

    values = np.array([
        traffic[column] for column in FEATURE_COLUMNS
    ]).reshape(1, -1)

    prediction = model.predict(values)[0]
    anomaly_score = -model.decision_function(values)[0]

    return {
        "classification": (
            "ANOMALOUS" if prediction == -1 else "NORMAL"
        ),
        "anomaly_score": round(float(anomaly_score), 4)
    }


if __name__ == "__main__":

    model = train_model()

    test_traffic = {
        "Normal Traffic": {
            "duration_seconds": 2,
            "source_bytes": 1200,
            "destination_bytes": 1500,
            "packet_count": 20,
            "failed_connections": 0,
            "connections_per_minute": 12
        },

        "Suspicious Traffic": {
            "duration_seconds": 500,
            "source_bytes": 5000000,
            "destination_bytes": 1000,
            "packet_count": 5000,
            "failed_connections": 100,
            "connections_per_minute": 900
        }
    }

    print("\n--- NeuroSphere Threat Detection Results ---")

    for name, traffic in test_traffic.items():

        result = detect_threat(model, traffic)

        print(f"\nTraffic: {name}")
        print(f"Classification: {result['classification']}")
        print(f"Anomaly Score: {result['anomaly_score']}")
