import sys
import os
import torch
import numpy as np
from PIL import Image
from torchvision import transforms
from deepface import DeepFace

# Add FocusFace repo to Python path
FOCUSFACE_REPO = os.path.join(os.path.dirname(__file__), "focusface", "FocusFace")
sys.path.append(FOCUSFACE_REPO)

import model


WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__),
    "focusface",
    "weights",
    "focus_face_w_pretrained.mdl"
)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_focusface_model():
    net = model.FocusFace(identities=85742)

    try:
        checkpoint = torch.load(WEIGHTS_PATH, map_location=DEVICE, weights_only=False)
    except TypeError:
        checkpoint = torch.load(WEIGHTS_PATH, map_location=DEVICE)

    if isinstance(checkpoint, torch.nn.Module):
        net = checkpoint
    else:
        if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
            checkpoint = checkpoint["state_dict"]

        clean_state = {}
        for key, value in checkpoint.items():
            new_key = key.replace("module.", "")
            clean_state[new_key] = value

        net.load_state_dict(clean_state, strict=False)

    net.to(DEVICE)
    net.eval()
    return net


transform = transforms.Compose([
    transforms.Resize((112, 112)),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])


def extract_aligned_face(image_path):
    faces = DeepFace.extract_faces(
        img_path=image_path,
        detector_backend="retinaface",
        enforce_detection=False,
        align=True
    )

    face = faces[0]["face"]

    if face.max() <= 1:
        face = (face * 255).astype(np.uint8)
    else:
        face = face.astype(np.uint8)

    return Image.fromarray(face)


def get_focusface_embedding(net, image_path):
    face_img = extract_aligned_face(image_path)
    tensor = transform(face_img).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        _, embedding, _, mask_score = net(tensor, inference=True)

    embedding = embedding.cpu().numpy()[0]
    embedding = embedding / np.linalg.norm(embedding)

    return embedding, float(mask_score.cpu().numpy()[0])


def cosine_similarity(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage:")
        print("python focusface_test.py clear_face.jpg masked_face.jpg")
        sys.exit(1)

    img1 = sys.argv[1]
    img2 = sys.argv[2]

    net = load_focusface_model()

    emb1, mask1 = get_focusface_embedding(net, img1)
    emb2, mask2 = get_focusface_embedding(net, img2)

    score = cosine_similarity(emb1, emb2)

    print("FocusFace similarity:", score)
    print("Image 1 mask score:", mask1)
    print("Image 2 mask score:", mask2)