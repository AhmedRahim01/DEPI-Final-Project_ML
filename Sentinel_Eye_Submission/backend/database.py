import os
import sqlite3
import numpy as np
from datetime import datetime

# Try importing PostgreSQL client and pgvector
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from pgvector.psycopg2 import register_vector
    PSYGOPG2_AVAILABLE = True
except ImportError:
    PSYGOPG2_AVAILABLE = False

DB_FILE = os.path.join(os.path.dirname(__file__), "biometric.db")

# Connection details for PostgreSQL (overrideable via environment variables)
PG_HOST = os.getenv("PGHOST", "localhost")
PG_PORT = os.getenv("PGPORT", "5432")
PG_DB = os.getenv("PGDATABASE", "sentinel_eye")
PG_USER = os.getenv("PGUSER", "postgres")
PG_PASSWORD = os.getenv("PGPASSWORD", "postgres")

# Global flag to track which DB engine we are using
USE_POSTGRES = False

def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def normalize_embedding(embedding):
    embedding = np.array(embedding, dtype=np.float32)
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm

def try_postgres_connection():
    if not PSYGOPG2_AVAILABLE:
        return None
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD,
            connect_timeout=3
        )
        return conn
    except Exception:
        return None

def init_db():
    global USE_POSTGRES
    
    conn = try_postgres_connection()
    if conn is not None:
        USE_POSTGRES = True
        print("[DB INIT] Using PostgreSQL database backend.")
        try:
            cur = conn.cursor()
            # Enable vector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Create identities table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS identities (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    nationality VARCHAR(100),
                    dob VARCHAR(50),
                    passport_number VARCHAR(100),
                    enrollment_site VARCHAR(100),
                    enrolled_by VARCHAR(100),
                    enrolled_at VARCHAR(50),
                    watchlist_tier INT
                );
            """)
            
            # Create biometric_embeddings table with pgvector type (VECTOR(512))
            cur.execute("""
                CREATE TABLE IF NOT EXISTS biometric_embeddings (
                    id SERIAL PRIMARY KEY,
                    identity_id INT REFERENCES identities(id) ON DELETE CASCADE,
                    modality VARCHAR(50),
                    embedding VECTOR(512) NOT NULL,
                    model_version VARCHAR(50),
                    captured_at VARCHAR(50)
                );
            """)
            
            # Create HNSW index for cosine operations
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_biometric_embeddings_hnsw 
                ON biometric_embeddings USING hnsw (embedding vector_cosine_ops);
            """)
            
            # Create search_log table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS search_log (
                    id SERIAL PRIMARY KEY,
                    query_embedding VECTOR(512),
                    top1_identity_id INT REFERENCES identities(id),
                    top1_score REAL,
                    alert_level VARCHAR(50),
                    operator_id VARCHAR(100),
                    camera_id VARCHAR(100),
                    site_id VARCHAR(100),
                    timestamp VARCHAR(50)
                );
            """)
            
            # Create alert_log table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS alert_log (
                    id SERIAL PRIMARY KEY,
                    search_log_id INT REFERENCES search_log(id),
                    status VARCHAR(50),
                    reviewed_by VARCHAR(100),
                    reviewed_at VARCHAR(50),
                    notes TEXT
                );
            """)
            
            # Create watchlist_sync_log table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS watchlist_sync_log (
                    id SERIAL PRIMARY KEY,
                    source VARCHAR(100),
                    received_at VARCHAR(50),
                    records_added INT,
                    records_updated INT,
                    sync_status VARCHAR(50)
                );
            """)
            
            conn.commit()
            cur.close()
            conn.close()
            return
        except Exception as e:
            print(f"[DB INIT] PostgreSQL initialization failed: {e}. Falling back to SQLite.")
            conn.close()
            
    # SQLite Fallback
    USE_POSTGRES = False
    print("[DB INIT] Using SQLite database backend.")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS identities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            nationality TEXT,
            dob TEXT,
            passport_number TEXT,
            enrollment_site TEXT,
            enrolled_by TEXT,
            enrolled_at TEXT,
            watchlist_tier INTEGER
        );
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS biometric_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identity_id INTEGER REFERENCES identities(id) ON DELETE CASCADE,
            modality TEXT,
            embedding BLOB NOT NULL,
            model_version TEXT,
            captured_at TEXT
        );
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS search_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_embedding BLOB,
            top1_identity_id INTEGER REFERENCES identities(id),
            top1_score REAL,
            alert_level TEXT,
            operator_id TEXT,
            camera_id TEXT,
            site_id TEXT,
            timestamp TEXT
        );
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS alert_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_log_id INTEGER REFERENCES search_log(id),
            status TEXT,
            reviewed_by TEXT,
            reviewed_at TEXT,
            notes TEXT
        );
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS watchlist_sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            received_at TEXT,
            records_added INTEGER,
            records_updated INTEGER,
            sync_status TEXT
        );
    """)
    
    conn.commit()
    conn.close()

def get_connection():
    if USE_POSTGRES:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
        register_vector(conn)
        return conn
    else:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn

def register_identity(name, nationality, dob, passport_number, enrollment_site, enrolled_by, watchlist_tier, embedding, modality="face", model_version="Ensemble v1"):
    conn = get_connection()
    cur = conn.cursor()
    
    normalized_emb = normalize_embedding(embedding)
    
    try:
        # Check if identity exists or insert
        if USE_POSTGRES:
            cur.execute("SELECT id FROM identities WHERE name = %s", (name,))
            row = cur.fetchone()
            if row:
                identity_id = row[0]
            else:
                cur.execute("""
                    INSERT INTO identities (name, nationality, dob, passport_number, enrollment_site, enrolled_by, enrolled_at, watchlist_tier)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (name, nationality, dob, passport_number, enrollment_site, enrolled_by, get_time(), watchlist_tier))
                identity_id = cur.fetchone()[0]
                
            cur.execute("""
                INSERT INTO biometric_embeddings (identity_id, modality, embedding, model_version, captured_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (identity_id, modality, normalized_emb, model_version, get_time()))
        else:
            cur.execute("SELECT id FROM identities WHERE name = ?", (name,))
            row = cur.fetchone()
            if row:
                identity_id = row["id"]
            else:
                cur.execute("""
                    INSERT INTO identities (name, nationality, dob, passport_number, enrollment_site, enrolled_by, enrolled_at, watchlist_tier)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, nationality, dob, passport_number, enrollment_site, enrolled_by, get_time(), watchlist_tier))
                identity_id = cur.lastrowid
                
            embedding_blob = np.array(normalized_emb, dtype=np.float32).tobytes()
            cur.execute("""
                INSERT INTO biometric_embeddings (identity_id, modality, embedding, model_version, captured_at)
                VALUES (?, ?, ?, ?, ?)
            """, (identity_id, modality, embedding_blob, model_version, get_time()))
            
        conn.commit()
        return identity_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def search_best_matches(query_embedding, top_k=3):
    conn = get_connection()
    cur = conn.cursor()
    
    normalized_q = normalize_embedding(query_embedding)
    
    if USE_POSTGRES:
        try:
            # Native pgvector cosine search: <=> operator represents cosine distance
            # Similarity is 1 - distance. We group by identity to get the best match per identity.
            cur.execute("""
                SELECT name, nationality, dob, passport_number, watchlist_tier, 1.0 - MIN(distance) AS score
                FROM (
                    SELECT i.name, i.nationality, i.dob, i.passport_number, i.watchlist_tier, (b.embedding <=> %s) AS distance
                    FROM biometric_embeddings b
                    JOIN identities i ON b.identity_id = i.id
                ) sub
                GROUP BY name, nationality, dob, passport_number, watchlist_tier
                ORDER BY score DESC
                LIMIT %s
            """, (normalized_q, top_k))
            
            rows = cur.fetchall()
            results = []
            for row in rows:
                results.append({
                    "name": row[0],
                    "nationality": row[1],
                    "dob": row[2],
                    "passport_number": row[3],
                    "watchlist_tier": row[4],
                    "score": round(float(row[5]), 4)
                })
            return results, "pgvector Native Search"
        except Exception as e:
            print(f"[DB SEARCH] PostgreSQL search failed: {e}")
            return [], "Error"
        finally:
            cur.close()
            conn.close()
    else:
        try:
            cur.execute("""
                SELECT i.id, i.name, i.nationality, i.dob, i.passport_number, i.watchlist_tier, b.embedding 
                FROM biometric_embeddings b 
                JOIN identities i ON b.identity_id = i.id
            """)
            rows = cur.fetchall()
            if not rows:
                return [], "SQLite Cosine Fallback"
                
            identity_best_scores = {}
            for row in rows:
                name = row["name"]
                nationality = row["nationality"]
                dob = row["dob"]
                passport_number = row["passport_number"]
                watchlist_tier = row["watchlist_tier"]
                
                stored_emb = np.frombuffer(row["embedding"], dtype=np.float32)
                stored_emb = normalize_embedding(stored_emb)
                
                score = float(np.dot(normalized_q, stored_emb))
                
                key = (name, nationality, dob, passport_number, watchlist_tier)
                if key not in identity_best_scores or score > identity_best_scores[key]:
                    identity_best_scores[key] = score
                    
            ranked = [
                {
                    "name": k[0],
                    "nationality": k[1],
                    "dob": k[2],
                    "passport_number": k[3],
                    "watchlist_tier": k[4],
                    "score": round(score, 4)
                }
                for k, score in identity_best_scores.items()
            ]
            ranked.sort(key=lambda x: x["score"], reverse=True)
            return ranked[:top_k], "SQLite Cosine Fallback"
        finally:
            cur.close()
            conn.close()

def log_search(query_embedding, top1_identity_name, top1_score, alert_level, operator_id="OP_01", camera_id="Camera 1", site_id="Cairo Airport"):
    conn = get_connection()
    cur = conn.cursor()
    
    normalized_q = normalize_embedding(query_embedding)
    
    try:
        identity_id = None
        if top1_identity_name and top1_identity_name != "Unknown":
            if USE_POSTGRES:
                cur.execute("SELECT id FROM identities WHERE name = %s", (top1_identity_name,))
                row = cur.fetchone()
                if row:
                    identity_id = row[0]
            else:
                cur.execute("SELECT id FROM identities WHERE name = ?", (top1_identity_name,))
                row = cur.fetchone()
                if row:
                    identity_id = row["id"]
                    
        timestamp = get_time()
        
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO search_log (query_embedding, top1_identity_id, top1_score, alert_level, operator_id, camera_id, site_id, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (normalized_q, identity_id, top1_score, alert_level, operator_id, camera_id, site_id, timestamp))
            search_log_id = cur.fetchone()[0]
        else:
            query_blob = np.array(normalized_q, dtype=np.float32).tobytes()
            cur.execute("""
                INSERT INTO search_log (query_embedding, top1_identity_id, top1_score, alert_level, operator_id, camera_id, site_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (query_blob, identity_id, top1_score, alert_level, operator_id, camera_id, site_id, timestamp))
            search_log_id = cur.lastrowid
            
        conn.commit()
        return search_log_id
    except Exception as e:
        print(f"[DB LOG] Log search failed: {e}")
        conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()

def log_alert(search_log_id, status="open", reviewed_by=None, notes=""):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        reviewed_at = get_time() if reviewed_by else None
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO alert_log (search_log_id, status, reviewed_by, reviewed_at, notes)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (search_log_id, status, reviewed_by, reviewed_at, notes))
            alert_id = cur.fetchone()[0]
        else:
            cur.execute("""
                INSERT INTO alert_log (search_log_id, status, reviewed_by, reviewed_at, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (search_log_id, status, reviewed_by, reviewed_at, notes))
            alert_id = cur.lastrowid
            
        conn.commit()
        return alert_id
    except Exception as e:
        print(f"[DB LOG] Log alert failed: {e}")
        conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()

def get_stats():
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cur.execute("SELECT COUNT(*) FROM identities")
            total_users = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM search_log")
            total_searches = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM alert_log")
            total_alerts = cur.fetchone()[0]
        else:
            cur.execute("SELECT COUNT(*) AS count FROM identities")
            total_users = cur.fetchone()["count"]
            
            cur.execute("SELECT COUNT(*) AS count FROM search_log")
            total_searches = cur.fetchone()["count"]
            
            cur.execute("SELECT COUNT(*) AS count FROM alert_log")
            total_alerts = cur.fetchone()["count"]
            
        return {
            "total_users": total_users,
            "total_searches": total_searches,
            "total_alerts": total_alerts,
            "db_type": "PostgreSQL + pgvector" if USE_POSTGRES else "SQLite Fallback"
        }
    except Exception as e:
        print(f"[DB STATS] Fetch stats failed: {e}")
        return {"total_users": 0, "total_searches": 0, "total_alerts": 0, "db_type": "Error"}
    finally:
        cur.close()
        conn.close()

def get_alerts(limit=20):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cur.execute("""
                SELECT a.id, i.name, s.top1_score AS score, s.alert_level, s.camera_id AS camera, s.timestamp AS created_at, a.status
                FROM alert_log a
                JOIN search_log s ON a.search_log_id = s.id
                JOIN identities i ON s.top1_identity_id = i.id
                ORDER BY a.id DESC LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
            alerts = []
            for row in rows:
                alerts.append({
                    "id": row[0],
                    "name": row[1],
                    "score": float(row[2]),
                    "alert_level": row[3],
                    "camera": row[4],
                    "created_at": row[5],
                    "status": row[6]
                })
        else:
            cur.execute("""
                SELECT a.id, i.name, s.top1_score AS score, s.alert_level, s.camera_id AS camera, s.timestamp AS created_at, a.status
                FROM alert_log a
                JOIN search_log s ON a.search_log_id = s.id
                JOIN identities i ON s.top1_identity_id = i.id
                ORDER BY a.id DESC LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
            alerts = []
            for row in rows:
                alerts.append({
                    "id": row["id"],
                    "name": row["name"],
                    "score": float(row["score"]),
                    "alert_level": row["alert_level"],
                    "camera": row["camera"],
                    "created_at": row["created_at"],
                    "status": row["status"]
                })
        return alerts
    except Exception as e:
        print(f"[DB ALERTS] Fetch alerts failed: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def get_searches(limit=20):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cur.execute("""
                SELECT s.id, COALESCE(i.name, 'Unknown') AS best_match, s.top1_score AS score, 
                       CASE WHEN s.top1_identity_id IS NOT NULL THEN 'match' ELSE 'unknown' END AS status,
                       s.camera_id AS camera, s.timestamp AS created_at
                FROM search_log s
                LEFT JOIN identities i ON s.top1_identity_id = i.id
                ORDER BY s.id DESC LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
            searches = []
            for row in rows:
                searches.append({
                    "id": row[0],
                    "best_match": row[1],
                    "score": float(row[2]),
                    "status": row[3],
                    "camera": row[4],
                    "created_at": row[5]
                })
        else:
            cur.execute("""
                SELECT s.id, COALESCE(i.name, 'Unknown') AS best_match, s.top1_score AS score,
                       CASE WHEN s.top1_identity_id IS NOT NULL THEN 'match' ELSE 'unknown' END AS status,
                       s.camera_id AS camera, s.timestamp AS created_at
                FROM search_log s
                LEFT JOIN identities i ON s.top1_identity_id = i.id
                ORDER BY s.id DESC LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
            searches = []
            for row in rows:
                searches.append({
                    "id": row["id"],
                    "best_match": row["best_match"],
                    "score": float(row["score"]),
                    "status": row["status"],
                    "camera": row["camera"],
                    "created_at": row["created_at"]
                })
        return searches
    except Exception as e:
        print(f"[DB SEARCHES] Fetch searches failed: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def get_watchlist():
    conn = get_connection()
    cur = conn.cursor()
    try:
        if USE_POSTGRES:
            cur.execute("""
                SELECT i.id, i.name, i.nationality, i.dob, i.passport_number, i.watchlist_tier, 
                       i.enrollment_site, i.enrolled_at, COUNT(b.id) as photo_count
                FROM identities i
                LEFT JOIN biometric_embeddings b ON i.id = b.identity_id
                GROUP BY i.id, i.name, i.nationality, i.dob, i.passport_number, i.watchlist_tier, i.enrollment_site, i.enrolled_at
                ORDER BY i.id DESC
            """)
            rows = cur.fetchall()
            watchlist = []
            for row in rows:
                watchlist.append({
                    "id": row[0],
                    "name": row[1],
                    "nationality": row[2],
                    "dob": row[3],
                    "passport_number": row[4],
                    "watchlist_tier": row[5],
                    "enrollment_site": row[6],
                    "created_at": row[7],
                    "photo_count": row[8]
                })
            return watchlist
        else:
            cur.execute("""
                SELECT i.id, i.name, i.nationality, i.dob, i.passport_number, i.watchlist_tier, 
                       i.enrollment_site, i.enrolled_at, COUNT(b.id) as photo_count
                FROM identities i
                LEFT JOIN biometric_embeddings b ON i.id = b.identity_id
                GROUP BY i.id
                ORDER BY i.id DESC
            """)
            rows = cur.fetchall()
            watchlist = []
            for row in rows:
                watchlist.append({
                    "id": row["id"],
                    "name": row["name"],
                    "nationality": row["nationality"],
                    "dob": row["dob"],
                    "passport_number": row["passport_number"],
                    "watchlist_tier": row["watchlist_tier"],
                    "enrollment_site": row["enrollment_site"],
                    "created_at": row["enrolled_at"],
                    "photo_count": row["photo_count"]
                })
            return watchlist
    except Exception as e:
        print(f"[DB GET WATCHLIST] Fetch watchlist failed: {e}")
        return []
    finally:
        cur.close()
        conn.close()

# Initialize DB when this file is imported
init_db()
