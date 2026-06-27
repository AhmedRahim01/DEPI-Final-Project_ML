import sqlite3
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from datetime import datetime

from focusface_engine import get_focusface_embedding

app = FastAPI(title="Sentinel Eye API - FocusFace")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "biometric.db"

# FocusFace gives one embedding vector.
# We do not use DeepFace Facenet512 + ArcFace now.
NORMAL_MATCH_THRESHOLD = 0.45
ROBUST_MATCH_THRESHOLD = 0.35
STRONG_MATCH_THRESHOLD = 0.60


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            embedding BLOB NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            score REAL NOT NULL,
            confidence TEXT NOT NULL,
            mode TEXT NOT NULL,
            camera TEXT DEFAULT 'Unknown Camera',
            alert_level TEXT DEFAULT 'possible',
            created_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            best_match TEXT NOT NULL,
            score REAL NOT NULL,
            confidence TEXT NOT NULL,
            mode TEXT NOT NULL,
            camera TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    c.execute("PRAGMA table_info(alerts)")
    columns = [col[1] for col in c.fetchall()]

    if "camera" not in columns:
        c.execute("ALTER TABLE alerts ADD COLUMN camera TEXT DEFAULT 'Unknown Camera'")

    if "alert_level" not in columns:
        c.execute("ALTER TABLE alerts ADD COLUMN alert_level TEXT DEFAULT 'possible'")

    conn.commit()
    conn.close()


init_db()


def cosine_similarity(a, b):
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return -1.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def get_embedding(img_path):
    """
    FocusFace embedding.
    This is used for both clear and masked faces.
    """
    embedding, mask_score = get_focusface_embedding(img_path)
    return embedding, mask_score


def get_active_threshold(mode):
    if mode == "robust":
        return ROBUST_MATCH_THRESHOLD

    return NORMAL_MATCH_THRESHOLD


def get_alert_level(score, mode):
    if score >= STRONG_MATCH_THRESHOLD:
        return "strong"

    if score >= NORMAL_MATCH_THRESHOLD:
        return "possible"

    if mode == "robust" and score >= ROBUST_MATCH_THRESHOLD:
        return "low possible"

    return "unknown"


def save_alert(name, score, confidence, mode, camera, alert_level):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute(
        """
        INSERT INTO alerts (name, score, confidence, mode, camera, alert_level, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            float(score),
            confidence,
            mode,
            camera,
            alert_level,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    conn.commit()
    conn.close()


def save_search(best_match, score, confidence, mode, camera, status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute(
        """
        INSERT INTO searches (best_match, score, confidence, mode, camera, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            best_match,
            float(score),
            confidence,
            mode,
            camera,
            status,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    conn.commit()
    conn.close()


@app.get("/")
def root():
    return {
        "message": "Sentinel Eye API with FocusFace is running"
    }


@app.get("/stats")
def stats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM alerts")
    total_alerts = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM searches")
    total_searches = c.fetchone()[0]

    conn.close()

    return {
        "total_users": total_users,
        "total_alerts": total_alerts,
        "total_searches": total_searches
    }


@app.get("/alerts")
def get_alerts():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        SELECT id, name, score, confidence, mode, camera, alert_level, created_at
        FROM alerts
        ORDER BY id DESC
        LIMIT 20
    """)

    rows = c.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "name": row[1],
            "score": row[2],
            "confidence": row[3],
            "mode": row[4],
            "camera": row[5],
            "alert_level": row[6],
            "created_at": row[7],
        }
        for row in rows
    ]


@app.get("/searches")
def get_searches():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        SELECT id, best_match, score, confidence, mode, camera, status, created_at
        FROM searches
        ORDER BY id DESC
        LIMIT 20
    """)

    rows = c.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "best_match": row[1],
            "score": row[2],
            "confidence": row[3],
            "mode": row[4],
            "camera": row[5],
            "status": row[6],
            "created_at": row[7],
        }
        for row in rows
    ]


@app.post("/register")
async def register(name: str = Form(...), file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    temp_filename = f"temp_{uuid.uuid4().hex}.jpg"

    with open(temp_filename, "wb") as f:
        f.write(await file.read())

    try:
        embedding, mask_score = get_embedding(temp_filename)

        if embedding is None:
            raise HTTPException(
                status_code=400,
                detail="No usable face information detected in the image."
            )

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        c.execute("SELECT id FROM users WHERE name=?", (name,))
        if c.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="User already exists.")

        c.execute(
            "INSERT INTO users (name, embedding) VALUES (?, ?)",
            (name, embedding.tobytes())
        )

        conn.commit()
        conn.close()

        return {
            "message": f"Successfully registered user: {name}",
            "embedding_size": int(len(embedding)),
            "mask_score": mask_score
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


@app.post("/recognize")
async def recognize(
    file: UploadFile = File(...),
    mode: str = Form("normal"),
    camera: str = Form("Camera 1 - Main Gate")
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if mode not in ["normal", "robust"]:
        mode = "normal"

    temp_filename = f"temp_{uuid.uuid4().hex}.jpg"

    with open(temp_filename, "wb") as f:
        f.write(await file.read())

    try:
        query_embedding, mask_score = get_embedding(temp_filename)

        if query_embedding is None:
            raise HTTPException(
                status_code=400,
                detail="Could not extract enough face information from the image."
            )

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT name, embedding FROM users")
        rows = c.fetchall()
        conn.close()

        if len(rows) == 0:
            save_search("Unknown Person", 0.0, "none", mode, camera, "unknown")

            return {
                "match": False,
                "name": "Unknown Person",
                "score": 0.0,
                "confidence": "none",
                "alert_level": "unknown",
                "mode": mode,
                "camera": camera,
                "mask_score": mask_score,
                "top_matches": [],
                "alert": {"generated": False}
            }

        all_matches = []

        for name, emb_bytes in rows:
            db_embedding = np.frombuffer(emb_bytes, dtype=np.float32)

            if len(db_embedding) != len(query_embedding):
                continue

            score = cosine_similarity(query_embedding, db_embedding)

            all_matches.append({
                "name": name,
                "score": float(score)
            })

        all_matches.sort(key=lambda x: x["score"], reverse=True)
        top_matches = all_matches[:3]

        if len(top_matches) == 0:
            save_search("Unknown Person", 0.0, "none", mode, camera, "unknown")

            return {
                "match": False,
                "name": "Unknown Person",
                "score": 0.0,
                "confidence": "none",
                "alert_level": "unknown",
                "mode": mode,
                "camera": camera,
                "mask_score": mask_score,
                "top_matches": [],
                "alert": {"generated": False}
            }

        best = top_matches[0]
        best_score = best["score"]
        best_name = best["name"]

        active_threshold = get_active_threshold(mode)
        alert_level = get_alert_level(best_score, mode)

        if best_score >= active_threshold:
            confidence = alert_level
            status = "matched"

            save_search(best_name, best_score, confidence, mode, camera, status)
            save_alert(best_name, best_score, confidence, mode, camera, alert_level)

            return {
                "match": True,
                "name": best_name,
                "score": float(best_score),
                "confidence": confidence,
                "alert_level": alert_level,
                "mode": mode,
                "camera": camera,
                "mask_score": mask_score,
                "top_matches": top_matches,
                "alert": {
                    "generated": True,
                    "message": f"Alert generated for {best_name} at {camera}"
                }
            }

        save_search("Unknown Person", best_score, "none", mode, camera, "unknown")

        return {
            "match": False,
            "name": "Unknown Person",
            "score": float(best_score),
            "confidence": "none",
            "alert_level": "unknown",
            "mode": mode,
            "camera": camera,
            "mask_score": mask_score,
            "top_matches": top_matches,
            "alert": {
                "generated": False,
                "message": "No alert generated"
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)