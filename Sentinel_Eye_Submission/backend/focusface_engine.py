import os
import sys
import torch
import numpy as np
from PIL import Image
from torchvision import transforms
from deepface import DeepFace

BACKEND_DIR = os.path.dirname(__file__)
PROJECT_DIR = os.path.dirname(BACKEND_DIR)

FOCUSFACE_REPO = os.path.join(PROJECT_DIR, "focusface", "FocusFace")
WEIGHTS_PATH = os.path.join(
    PROJECT_DIR,
    "focusface",
    "weights",
    "focus_face_w_pretrained.mdl"
)

sys.path.append(FOCUSFACE_REPO)

import model

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_focusface_model = None

transform = transforms.Compose([
    transforms.Resize((112, 112)),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])


def load_focusface_model():
    global _focusface_model

    if _focusface_model is not None:
        return _focusface_model

    if not os.path.exists(WEIGHTS_PATH):
        raise FileNotFoundError(f"FocusFace weights not found at: {WEIGHTS_PATH}")

    net = model.FocusFace(identities=85742)

    checkpoint = torch.load(
        WEIGHTS_PATH,
        map_location=DEVICE,
        weights_only=False
    )

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

    _focusface_model = net
    return _focusface_model


def extract_aligned_face(image_path):
    faces = DeepFace.extract_faces(
        img_path=image_path,
        detector_backend="retinaface",
        enforce_detection=False,
        align=True
    )

    if len(faces) == 0:
        raise Exception("No face detected")

    face = faces[0]["face"]

    if face.max() <= 1:
        face = (face * 255).astype(np.uint8)
    else:
        face = face.astype(np.uint8)

    return Image.fromarray(face)


def normalize_embedding(embedding):
    embedding = np.array(embedding, dtype=np.float32)
    norm = np.linalg.norm(embedding)

    if norm == 0:
        return embedding

    return embedding / norm


def get_focusface_embedding(image_path):
    net = load_focusface_model()

    face_img = extract_aligned_face(image_path)
    tensor = transform(face_img).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        output = net(tensor, inference=True)

    embedding = output[1]
    embedding = embedding.cpu().numpy()[0]
    embedding = normalize_embedding(embedding)

    mask_score = None

    if len(output) >= 4:
        try:
            mask_score = float(output[3].cpu().numpy()[0])
        except Exception:
            mask_score = None

    return embedding.astype(np.float32), mask_score


def get_ensemble_embedding(image_path):
    # 1. Get FocusFace embedding (already normalized)
    focus_emb, mask_score = get_focusface_embedding(image_path)
    
    # 2. Get ArcFace embedding using DeepFace
    try:
        res = DeepFace.represent(img_path=image_path, model_name="ArcFace", enforce_detection=False)
        arc_emb = np.array(res[0]["embedding"], dtype=np.float32)
        arc_emb = normalize_embedding(arc_emb)
    except Exception as e:
        print(f"[FocusFace Engine] Error extracting ArcFace embedding: {e}")
        arc_emb = None
        
    # 3. Average the two embeddings if ArcFace succeeded, otherwise fallback to FocusFace
    if arc_emb is not None:
        ensemble_emb = (focus_emb + arc_emb) / 2.0
        ensemble_emb = normalize_embedding(ensemble_emb)
    else:
        ensemble_emb = focus_emb
        
    return ensemble_emb.astype(np.float32), mask_score