import sqlite3
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from deepface import DeepFace
import os
import uuid

app = FastAPI(title="Biometric Face Recognition API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "biometric.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            embedding BLOB NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_embedding(img_path):
    try:
        # Extract Facenet512 embedding using retinaface
        embedding_objs_facenet = DeepFace.represent(
            img_path=img_path, 
            model_name="Facenet512", 
            detector_backend="retinaface", 
            enforce_detection=True
        )
        if len(embedding_objs_facenet) == 0:
            return None
        facenet_emb = np.array(embedding_objs_facenet[0]["embedding"])

        # Extract ArcFace embedding using retinaface
        embedding_objs_arcface = DeepFace.represent(
            img_path=img_path, 
            model_name="ArcFace", 
            detector_backend="retinaface", 
            enforce_detection=True
        )
        if len(embedding_objs_arcface) == 0:
            return None
        arcface_emb = np.array(embedding_objs_arcface[0]["embedding"])

        # Combine both embeddings for simple BLOB storage
        return np.concatenate([facenet_emb, arcface_emb])
    except ValueError:
        # Deepface throws ValueError if no face is detected or if face is too heavily occluded
        return None
    except Exception:
        return None

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

@app.post("/register")
async def register(name: str = Form(...), file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Save file temporarily
    temp_filename = f"temp_{uuid.uuid4().hex}.jpg"
    with open(temp_filename, "wb") as f:
        f.write(await file.read())
        
    try:
        embedding = get_embedding(temp_filename)
        if embedding is None:
            raise HTTPException(status_code=400, detail="No face detected in the image.")
            
        # Store in DB
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Check if user already exists
        c.execute("SELECT id FROM users WHERE name=?", (name,))
        if c.fetchone():
            raise HTTPException(status_code=400, detail="User already exists.")
            
        # SQLite doesn't natively support arrays, so we store it as bytes
        c.execute("INSERT INTO users (name, embedding) VALUES (?, ?)", (name, embedding.tobytes()))
        conn.commit()
        conn.close()
        
        return {"message": f"Successfully registered user: {name}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@app.post("/recognize")
async def recognize(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
        
    temp_filename = f"temp_{uuid.uuid4().hex}.jpg"
    with open(temp_filename, "wb") as f:
        f.write(await file.read())
        
    try:
        query_embedding = get_embedding(temp_filename)
        if query_embedding is None:
            raise HTTPException(status_code=400, detail="No face detected in the image.")
            
        # Retrieve all users from DB
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT name, embedding FROM users")
        rows = c.fetchall()
        conn.close()
        
        best_match = None
        best_combined_score = -1.0
        
        THRESHOLD_ARCFACE = 0.68
        THRESHOLD_FACENET = 0.72
        
        # Query embedding contains 512 dimensions for Facenet512 and 512 dimensions for ArcFace
        query_facenet = query_embedding[:512]
        query_arcface = query_embedding[512:]
        
        for name, emb_bytes in rows:
            db_embedding = np.frombuffer(emb_bytes, dtype=np.float64)
            
            # Skip old database entries that might not be exactly 1024 dimensions
            if len(db_embedding) != 1024:
                continue
                
            db_facenet = db_embedding[:512]
            db_arcface = db_embedding[512:]
            
            score_facenet = cosine_similarity(query_facenet, db_facenet)
            score_arcface = cosine_similarity(query_arcface, db_arcface)
            
            # Require both models to meet their respective occlusion thresholds
            if score_facenet >= THRESHOLD_FACENET and score_arcface >= THRESHOLD_ARCFACE:
                combined_score = (score_facenet + score_arcface) / 2
                if combined_score > best_combined_score:
                    best_combined_score = combined_score
                    best_match = name
                    
        if best_match:
            return {"match": True, "name": best_match, "score": float(best_combined_score)}
        else:
            return {"match": False, "name": "Unknown Person", "score": float(best_combined_score) if best_combined_score != -1.0 else 0.0}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
