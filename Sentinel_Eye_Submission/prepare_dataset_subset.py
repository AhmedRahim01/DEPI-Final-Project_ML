import os
import shutil

# CHANGE THESE TWO PATHS TO YOUR EXTRACTED DATASET PATHS
SRC_UNMASKED = r"C:\Users\lenvo\Desktop\DEPI-Final-Project_ML-main\dataset\RMFRD\unmasked\AFDB_face_dataset\AFDB_face_dataset"
SRC_MASKED = r"C:\Users\lenvo\Desktop\DEPI-Final-Project_ML-main\dataset\RMFRD\masked\AFDB_masked_face_dataset\AFDB_masked_face_dataset"

DEST_UNMASKED = r"dataset\RMFRD\unmasked"
DEST_MASKED = r"dataset\RMFRD\masked"

MAX_IDENTITIES = 20
MAX_IMAGES_PER_PERSON = 5

VALID_EXTENSIONS = [".jpg", ".jpeg", ".png"]


def get_images(folder):
    images = []

    for file in os.listdir(folder):
        ext = os.path.splitext(file.lower())[1]

        if ext in VALID_EXTENSIONS:
            images.append(os.path.join(folder, file))

    return images[:MAX_IMAGES_PER_PERSON]


def copy_subset():
    os.makedirs(DEST_UNMASKED, exist_ok=True)
    os.makedirs(DEST_MASKED, exist_ok=True)

    unmasked_people = set(os.listdir(SRC_UNMASKED))
    masked_people = set(os.listdir(SRC_MASKED))

    common_people = sorted(list(unmasked_people.intersection(masked_people)))
    selected_people = common_people[:MAX_IDENTITIES]

    print(f"Found common identities: {len(common_people)}")
    print(f"Copying selected identities: {len(selected_people)}")

    for person in selected_people:
        src_clear_person = os.path.join(SRC_UNMASKED, person)
        src_masked_person = os.path.join(SRC_MASKED, person)

        if not os.path.isdir(src_clear_person) or not os.path.isdir(src_masked_person):
            continue

        clear_images = get_images(src_clear_person)
        masked_images = get_images(src_masked_person)

        if len(clear_images) == 0 or len(masked_images) == 0:
            continue

        dest_clear_person = os.path.join(DEST_UNMASKED, person)
        dest_masked_person = os.path.join(DEST_MASKED, person)

        os.makedirs(dest_clear_person, exist_ok=True)
        os.makedirs(dest_masked_person, exist_ok=True)

        for img in clear_images:
            shutil.copy(img, dest_clear_person)

        for img in masked_images:
            shutil.copy(img, dest_masked_person)

        print(f"Copied: {person}")

    print("Done creating dataset subset.")


if __name__ == "__main__":
    copy_subset()