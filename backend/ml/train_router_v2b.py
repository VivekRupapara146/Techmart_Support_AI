"""
Trains Router v2b: TF-IDF + Logistic Regression on Banking77, mapped down
to our 5 support categories. One-off offline training — not part of the
API request path (Instruction 5: simplest maintainable solution; no
hyperparameter-tuning rabbit hole, one classifier, get it working,
measure it, move on, per the M0 scope boundary for v2b).

Run: python -m ml.train_router_v2b
Produces: artifacts/router_v2b/model.joblib
"""
import csv
import sys
import time

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report

from ml.banking77_mapping import BANKING77_TO_DOMAIN

TRAIN_CSV = "banking77_train.csv"  # relative to backend/ working dir (downloaded from PolyAI-LDN/task-specific-datasets)
TEST_CSV = "banking77_test.csv"
ARTIFACT_PATH = "artifacts/router_v2b/model.joblib"


def load_dataset(path: str) -> tuple[list[str], list[str]]:
    texts, labels = [], []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            category = row["category"]
            if category not in BANKING77_TO_DOMAIN:
                raise ValueError(
                    f"Unmapped Banking77 category found in data: {category!r}. "
                    f"BANKING77_TO_DOMAIN is out of sync with the source file."
                )
            texts.append(row["text"])
            labels.append(BANKING77_TO_DOMAIN[category])
    return texts, labels


def verify_mapping_completeness(path: str) -> None:
    """Fail loudly BEFORE training if the mapping has a typo or is missing
    a category — silently dropping mislabeled data would corrupt the
    trained model without any visible error."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        actual_categories = {row["category"] for row in reader}

    mapped_categories = set(BANKING77_TO_DOMAIN.keys())
    missing = actual_categories - mapped_categories
    extra = mapped_categories - actual_categories

    if missing:
        raise ValueError(f"BANKING77_TO_DOMAIN is missing categories present in the data: {sorted(missing)}")
    if extra:
        raise ValueError(f"BANKING77_TO_DOMAIN has categories NOT present in the data (typo?): {sorted(extra)}")

    print(f"Mapping completeness verified: all {len(actual_categories)} categories accounted for.")


def train() -> None:
    verify_mapping_completeness(TRAIN_CSV)

    train_texts, train_labels = load_dataset(TRAIN_CSV)
    test_texts, test_labels = load_dataset(TEST_CSV)
    print(f"Loaded {len(train_texts)} training examples, {len(test_texts)} test examples.")

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2), sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=1000, C=5.0, class_weight="balanced")),
    ])

    start = time.time()
    pipeline.fit(train_texts, train_labels)
    train_time = time.time() - start
    print(f"Training completed in {train_time:.2f}s")

    predictions = pipeline.predict(test_texts)
    accuracy = accuracy_score(test_labels, predictions)
    print(f"\nTest accuracy: {accuracy:.4f}")
    print("\nPer-class report:")
    print(classification_report(test_labels, predictions))

    import os
    os.makedirs("artifacts/router_v2b", exist_ok=True)
    joblib.dump(pipeline, ARTIFACT_PATH)
    print(f"\nModel saved to {ARTIFACT_PATH}")


if __name__ == "__main__":
    train()
