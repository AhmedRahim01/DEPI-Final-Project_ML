import os
import sys
import csv
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except Exception:
    faiss = None
    FAISS_AVAILABLE = False


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_DIR, "backend")
sys.path.append(BACKEND_DIR)

from focusface_engine import get_ensemble_embedding


UNMASKED_DIR = r"dataset\RMFRD\unmasked"
MASKED_DIR = r"dataset\RMFRD\masked"

RESULTS_FILE = "rmfrd_faiss_results.csv"

MAX_IDENTITIES = 20
MAX_GALLERY_IMAGES_PER_PERSON = 5
MAX_TEST_IMAGES_PER_PERSON = 5

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def get_images(folder_path):
    if not os.path.exists(folder_path):
        return []

    images = []

    for file_name in sorted(os.listdir(folder_path)):
        if file_name.lower().endswith(IMAGE_EXTENSIONS):
            images.append(os.path.join(folder_path, file_name))

    return images


def normalize_embedding(embedding):
    embedding = np.array(embedding, dtype=np.float32)
    norm = np.linalg.norm(embedding)

    if norm == 0:
        return embedding

    return embedding / norm


def get_common_identities():
    unmasked_people = set(os.listdir(UNMASKED_DIR))
    masked_people = set(os.listdir(MASKED_DIR))

    common_people = sorted(list(unmasked_people.intersection(masked_people)))

    return common_people[:MAX_IDENTITIES]


def build_gallery(identities):
    gallery_names = []
    gallery_embeddings = []

    print("Building FAISS gallery from unmasked images...")
    print("-" * 40)

    for identity in identities:
        identity_folder = os.path.join(UNMASKED_DIR, identity)
        images = get_images(identity_folder)[:MAX_GALLERY_IMAGES_PER_PERSON]

        for image_path in images:
            try:
                embedding, mask_score = get_ensemble_embedding(image_path)
                embedding = normalize_embedding(embedding)

                gallery_names.append(identity)
                gallery_embeddings.append(embedding)

                print(f"Added gallery image: {identity}")

            except Exception as e:
                print(f"Failed gallery image: {image_path}")
                print(e)

    if len(gallery_embeddings) == 0:
        return [], None

    gallery_matrix = np.vstack(gallery_embeddings).astype(np.float32)

    if FAISS_AVAILABLE:
        dimension = gallery_matrix.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(gallery_matrix)

        print("-" * 40)
        print("FAISS index created successfully")
        print(f"Gallery embeddings: {len(gallery_embeddings)}")
        print(f"Embedding dimension: {dimension}")
        print("-" * 40)

        return gallery_names, index

    print("FAISS not available. Using cosine fallback.")
    return gallery_names, gallery_matrix


def search_gallery(query_embedding, gallery_names, search_index, top_k=3):
    query_embedding = normalize_embedding(query_embedding).astype(np.float32)

    if FAISS_AVAILABLE:
        search_k = min(len(gallery_names), top_k * 5)

        scores, indexes = search_index.search(
            query_embedding.reshape(1, -1),
            search_k
        )

        raw_results = []

        for score, index_id in zip(scores[0], indexes[0]):
            if index_id == -1:
                continue

            raw_results.append({
                "name": gallery_names[index_id],
                "score": float(score)
            })

    else:
        gallery_matrix = search_index
        scores = gallery_matrix @ query_embedding
        indexes = np.argsort(scores)[::-1][:top_k * 5]

        raw_results = []

        for index_id in indexes:
            raw_results.append({
                "name": gallery_names[index_id],
                "score": float(scores[index_id])
            })

    best_by_identity = {}

    for result in raw_results:
        name = result["name"]
        score = result["score"]

        if name not in best_by_identity or score > best_by_identity[name]:
            best_by_identity[name] = score

    final_results = [
        {
            "name": name,
            "score": score
        }
        for name, score in best_by_identity.items()
    ]

    final_results.sort(key=lambda item: item["score"], reverse=True)

    return final_results[:top_k]


def evaluate():
    print("FAISS available:", FAISS_AVAILABLE)
    print("=" * 40)

    identities = get_common_identities()

    print(f"Selected identities: {len(identities)}")
    print("=" * 40)

    gallery_names, search_index = build_gallery(identities)

    if search_index is None:
        print("No gallery embeddings found.")
        return

    total_tests = 0
    top1_correct = 0
    top3_correct = 0

    rows = []

    print("Testing masked images...")
    print("=" * 40)

    for identity in identities:
        masked_folder = os.path.join(MASKED_DIR, identity)
        test_images = get_images(masked_folder)[:MAX_TEST_IMAGES_PER_PERSON]

        for image_path in test_images:
            try:
                query_embedding, mask_score = get_ensemble_embedding(image_path)

                top_matches = search_gallery(
                    query_embedding,
                    gallery_names,
                    search_index,
                    top_k=3
                )

                if not top_matches:
                    continue

                total_tests += 1

                top1_name = top_matches[0]["name"]
                top1_score = top_matches[0]["score"]

                top3_names = [match["name"] for match in top_matches]

                is_top1_correct = top1_name == identity
                is_top3_correct = identity in top3_names

                if is_top1_correct:
                    top1_correct += 1

                if is_top3_correct:
                    top3_correct += 1

                print(
                    f"Actual: {identity} | "
                    f"Top1: {top1_name} | "
                    f"Score: {round(top1_score * 100, 2)}% | "
                    f"Top1 correct: {is_top1_correct} | "
                    f"Top3 correct: {is_top3_correct}"
                )

                rows.append({
                    "actual_identity": identity,
                    "image_path": image_path,
                    "top1_prediction": top1_name,
                    "top1_score": round(top1_score * 100, 2),
                    "top1_correct": is_top1_correct,
                    "top3_predictions": ", ".join(top3_names),
                    "top3_correct": is_top3_correct,
                    "search_method": "FAISS IndexFlatIP" if FAISS_AVAILABLE else "Cosine fallback"
                })

            except Exception as e:
                print(f"Failed test image: {image_path}")
                print(e)

    if total_tests == 0:
        print("No tests completed.")
        return

    top1_accuracy = (top1_correct / total_tests) * 100
    top3_accuracy = (top3_correct / total_tests) * 100

    print("-" * 40)
    print(f"Total tests: {total_tests}")
    print(f"Top-1 Accuracy: {round(top1_accuracy, 2)}%")
    print(f"Top-3 Accuracy: {round(top3_accuracy, 2)}%")
    print("-" * 40)

    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "actual_identity",
                "image_path",
                "top1_prediction",
                "top1_score",
                "top1_correct",
                "top3_predictions",
                "top3_correct",
                "search_method"
            ]
        )

        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved results to: {RESULTS_FILE}")


if __name__ == "__main__":
    evaluate()