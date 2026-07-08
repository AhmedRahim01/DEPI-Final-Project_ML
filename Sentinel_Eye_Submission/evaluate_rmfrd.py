import os
import csv
import numpy as np
from backend.focusface_engine import get_ensemble_embedding

UNMASKED_DIR = r"dataset\RMFRD\unmasked"
MASKED_DIR = r"dataset\RMFRD\masked"
RESULTS_FILE = "rmfrd_results.csv"

MAX_IDENTITIES = 20
MAX_GALLERY_IMAGES_PER_PERSON = 5
MAX_TEST_IMAGES_PER_PERSON = 5

VALID_EXTENSIONS = [".jpg", ".jpeg", ".png"]


def cosine_similarity(a, b):
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return -1.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def get_images(folder, max_images):
    images = []

    for file in os.listdir(folder):
        ext = os.path.splitext(file.lower())[1]

        if ext in VALID_EXTENSIONS:
            images.append(os.path.join(folder, file))

    return images[:max_images]


def get_common_identities():
    unmasked_people = {
        name for name in os.listdir(UNMASKED_DIR)
        if os.path.isdir(os.path.join(UNMASKED_DIR, name))
    }

    masked_people = {
        name for name in os.listdir(MASKED_DIR)
        if os.path.isdir(os.path.join(MASKED_DIR, name))
    }

    common_people = sorted(list(unmasked_people.intersection(masked_people)))
    return common_people[:MAX_IDENTITIES]


def build_gallery(identities):
    gallery = []

    print(f"Building gallery from {len(identities)} identities...")

    for identity in identities:
        person_folder = os.path.join(UNMASKED_DIR, identity)
        images = get_images(person_folder, MAX_GALLERY_IMAGES_PER_PERSON)

        if len(images) == 0:
            continue

        for image_path in images:
            try:
                embedding, mask_score = get_ensemble_embedding(image_path)

                gallery.append({
                    "name": identity,
                    "embedding": embedding,
                    "image": image_path
                })

                print(f"Gallery added: {identity} | {os.path.basename(image_path)}")

            except Exception as e:
                print(f"Skipped gallery image {image_path}: {e}")

    return gallery


def search_gallery(query_embedding, gallery):
    identity_best_scores = {}

    for item in gallery:
        name = item["name"]
        score = cosine_similarity(query_embedding, item["embedding"])

        if name not in identity_best_scores:
            identity_best_scores[name] = score
        else:
            identity_best_scores[name] = max(identity_best_scores[name], score)

    ranked = [
        {
            "name": name,
            "score": score
        }
        for name, score in identity_best_scores.items()
    ]

    ranked.sort(key=lambda x: x["score"], reverse=True)

    return ranked


def evaluate(identities, gallery):
    if len(gallery) == 0:
        print("Gallery is empty. Check dataset folders.")
        return

    total_tests = 0
    top1_correct = 0
    top3_correct = 0

    rows = []

    print(f"Testing masked images for {len(identities)} identities...")

    for identity in identities:
        person_folder = os.path.join(MASKED_DIR, identity)
        test_images = get_images(person_folder, MAX_TEST_IMAGES_PER_PERSON)

        if len(test_images) == 0:
            continue

        for test_image in test_images:
            try:
                query_embedding, mask_score = get_ensemble_embedding(test_image)

                ranked = search_gallery(query_embedding, gallery)

                if len(ranked) == 0:
                    continue

                top1 = ranked[0]["name"]
                top1_score = ranked[0]["score"]
                top3 = [item["name"] for item in ranked[:3]]

                is_top1 = top1 == identity
                is_top3 = identity in top3

                total_tests += 1

                if is_top1:
                    top1_correct += 1

                if is_top3:
                    top3_correct += 1

                rows.append({
                    "actual_identity": identity,
                    "predicted_top1": top1,
                    "top1_score": round(top1_score, 4),
                    "top1_score_percent": round(top1_score * 100, 2),
                    "top3": " | ".join(top3),
                    "top1_correct": is_top1,
                    "top3_correct": is_top3,
                    "test_image": test_image
                })

                print(
                    f"Actual: {identity} | "
                    f"Top1: {top1} | "
                    f"Score: {round(top1_score * 100, 2)}% | "
                    f"Top1 correct: {is_top1} | "
                    f"Top3 correct: {is_top3}"
                )

            except Exception as e:
                print(f"Skipped test image {test_image}: {e}")

    if total_tests == 0:
        print("No tests completed. Check masked folder.")
        return

    top1_accuracy = top1_correct / total_tests
    top3_accuracy = top3_correct / total_tests

    print("--------------------------------")
    print(f"Total tests: {total_tests}")
    print(f"Top-1 Accuracy: {round(top1_accuracy * 100, 2)}%")
    print(f"Top-3 Accuracy: {round(top3_accuracy * 100, 2)}%")
    print("--------------------------------")

    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "actual_identity",
                "predicted_top1",
                "top1_score",
                "top1_score_percent",
                "top3",
                "top1_correct",
                "top3_correct",
                "test_image"
            ]
        )

        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved results to: {RESULTS_FILE}")


if __name__ == "__main__":
    identities = get_common_identities()

    print(f"Selected identities: {len(identities)}")
    print("--------------------------------")

    gallery = build_gallery(identities)

    print("--------------------------------")
    print(f"Total gallery embeddings: {len(gallery)}")
    print("--------------------------------")

    evaluate(identities, gallery)