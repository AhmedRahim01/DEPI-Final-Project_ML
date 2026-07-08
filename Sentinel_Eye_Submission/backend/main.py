from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import numpy as np
import tempfile
import os
import csv
import json
import sys
from typing import List, Optional
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool

from focusface_engine import get_ensemble_embedding
import database as db
import rag_engine

app = FastAPI(title="Sentinel Eye Production API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NORMAL_MATCH_THRESHOLD = 0.45
ROBUST_MATCH_THRESHOLD = 0.35
STRONG_MATCH_THRESHOLD = 0.60

def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

async def save_temp_file(uploaded_file: UploadFile):
    suffix = os.path.splitext(uploaded_file.filename)[1]
    if not suffix:
        suffix = ".jpg"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        content = await uploaded_file.read()
        temp.write(content)
        return temp.name

def classify_match(score, robust_mode):
    # Set operational thresholds matching UC-01
    critical_thresh = 0.75 if robust_mode else 0.80
    warning_thresh = 0.55 if robust_mode else 0.60

    if score >= critical_thresh:
        return "critical", "critical", True
    if score >= warning_thresh:
        return "warning", "warning", True
    if score >= 0.40:
        return "low", "low possible", False

    return "unknown", "unknown", False

# Role-Based Access Control (RBAC) Dependency Injection
def get_current_role(authorization: str = Header(None)):
    if not authorization:
        return "admin" # Default mock role for local development if no header is present
        
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return "operator"
        
    token = parts[1]
    if "admin" in token:
        return "admin"
    elif "supervisor" in token:
        return "supervisor"
    else:
        return "operator"

def require_role(allowed_roles: list):
    def dependency(role: str = Depends(get_current_role)):
        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: role '{role}' is unauthorized for this action. Required: {allowed_roles}"
            )
        return role
    return dependency

@app.post("/register")
async def register_identity(
    name: str = Form(...),
    nationality: str = Form("United States"),
    dob: str = Form("1990-01-01"),
    passport_number: str = Form("US1234567"),
    watchlist_tier: int = Form(3),  # 1=Red Notice, 2=Suspected, 3=POI
    enrollment_site: str = Form("Cairo International Airport"),
    files: List[UploadFile] = File(...),
    role: str = Depends(require_role(["admin", "supervisor"]))
):
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    processed_count = 0
    errors = []

    for file in files:
        temp_path = await save_temp_file(file)
        try:
            # Extract Ensemble Embedding (FocusFace + ArcFace)
            embedding, mask_score = get_ensemble_embedding(temp_path)
            
            # Save to database (will create identity or append to it)
            db.register_identity(
                name=name,
                nationality=nationality,
                dob=dob,
                passport_number=passport_number,
                enrollment_site=enrollment_site,
                enrolled_by=role,
                watchlist_tier=watchlist_tier,
                embedding=embedding,
                modality="face",
                model_version="Ensemble v1 (FocusFace+ArcFace)"
            )
            processed_count += 1
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    if processed_count == 0:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enroll biometrics. Errors: {'; '.join(errors)}"
        )

    msg = f"Enrolled {name} successfully with {processed_count} photo(s)."
    if errors:
        msg += f" (Warning: {len(errors)} files failed: {'; '.join(errors)})"

    return {
        "message": msg,
        "name": name,
        "enrolled_by": role,
        "processed_count": processed_count
    }

@app.post("/register/bulk")
async def register_bulk(
    watchlist_tier: int = Form(3),
    enrollment_site: str = Form("Bulk Import"),
    files: List[UploadFile] = File(...),
    role: str = Depends(require_role(["admin", "supervisor"]))
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for bulk upload")

    results = []
    success_count = 0

    for file in files:
        filename_without_ext = os.path.splitext(file.filename)[0]
        # Clean the name: replace underscores/dashes with spaces
        name = filename_without_ext.replace("_", " ").replace("-", " ").strip()
        # Capitalize each word
        name = " ".join([w.capitalize() for w in name.split()])

        if not name:
            results.append({"filename": file.filename, "status": "failed", "detail": "Empty name from filename"})
            continue

        temp_path = await save_temp_file(file)
        try:
            # Extract Ensemble Embedding (FocusFace + ArcFace)
            embedding, mask_score = get_ensemble_embedding(temp_path)
            
            # Save to database
            db.register_identity(
                name=name,
                nationality="Unknown",
                dob="Unknown",
                passport_number="Unknown",
                enrollment_site=enrollment_site,
                enrolled_by=role,
                watchlist_tier=watchlist_tier,
                embedding=embedding,
                modality="face",
                model_version="Ensemble v1 (FocusFace+ArcFace)"
            )
            results.append({"filename": file.filename, "name": name, "status": "success"})
            success_count += 1
        except Exception as e:
            results.append({"filename": file.filename, "name": name, "status": "failed", "detail": str(e)})
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    return {
        "message": f"Bulk import complete. Registered {success_count} of {len(files)} files.",
        "results": results,
        "success_count": success_count,
        "total_count": len(files)
    }

@app.post("/recognize")
async def recognize_face(
    file: UploadFile = File(...),
    robust_mode: bool = Form(False),
    camera: str = Form("Camera 1 - Main Gate"),
    role: str = Depends(require_role(["admin", "supervisor", "operator"]))
):
    temp_path = await save_temp_file(file)

    try:
        # Extract Ensemble Embedding (FocusFace + ArcFace)
        query_embedding, mask_score = get_ensemble_embedding(temp_path)

        # Retrieve top 3 matching identities
        top_matches, search_method = db.search_best_matches(query_embedding, top_k=3)

        if not top_matches:
            # Log search in DB as unknown
            db.log_search(
                query_embedding=query_embedding,
                top1_identity_name="Unknown",
                top1_score=0.0,
                alert_level="unknown",
                operator_id=role,
                camera_id=camera,
                site_id="Cairo Airport"
            )
            raise HTTPException(
                status_code=404,
                detail="No identities found in watchlist"
            )

        best_match = top_matches[0]
        best_name = best_match["name"]
        best_score = best_match["score"]

        confidence, alert_level, is_match = classify_match(best_score, robust_mode)

        mode = "robust" if robust_mode else "normal"

        # Log search in DB
        search_log_id = db.log_search(
            query_embedding=query_embedding,
            top1_identity_name=best_name if is_match else "Unknown",
            top1_score=best_score,
            alert_level=alert_level,
            operator_id=role,
            camera_id=camera,
            site_id="Cairo Airport"
        )

        # Log alert if verified match has critical or warning status
        if is_match and alert_level in ["critical", "warning"]:
            db.log_alert(
                search_log_id=search_log_id,
                status="open",
                reviewed_by=None,
                notes=f"Triggered {alert_level} threat level alert on {camera}"
            )

        return {
            "match": is_match,
            "name": best_name if is_match else "Unknown",
            "nationality": best_match["nationality"] if is_match else None,
            "dob": best_match["dob"] if is_match else None,
            "passport_number": best_match["passport_number"] if is_match else None,
            "watchlist_tier": best_match["watchlist_tier"] if is_match else None,
            "score": best_score,
            "confidence": confidence,
            "alert_level": alert_level,
            "mode": mode,
            "camera": camera,
            "mask_score": mask_score,
            "search_method": search_method,
            "top_matches": top_matches
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/stats")
async def get_stats():
    stats = db.get_stats()
    stats["recognition_model"] = "FocusFace + ArcFace Ensemble"
    stats["search_method"] = "PostgreSQL + FAISS Vector Search"
    return stats

@app.get("/alerts")
async def get_alerts():
    return db.get_alerts()

@app.get("/searches")
async def get_searches():
    return db.get_searches()

def calculate_metrics_from_csv(csv_path: str):
    if not os.path.exists(csv_path):
        return None
    
    total_tests = 0
    positive_tests = 0
    negative_tests = 0
    tp = 0
    fp = 0
    fn = 0
    tn = 0
    top1_correct_count = 0
    top3_correct_count = 0
    total_search_time = 0.0
    search_time_count = 0
    
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        original_headers = reader.fieldnames if reader.fieldnames else []
        header_map = {name.strip().lower(): name for name in original_headers}
        
        for row in reader:
            def get_val(keys):
                for k in keys:
                    if k in header_map:
                        return row[header_map[k]].strip()
                return ""
            
            total_tests += 1
            
            # Determine if it is a positive or negative test
            expected_match_str = get_val(['expected_match', 'actual_identity', 'true_identity'])
            is_positive = True
            if expected_match_str.lower() in ['false', '0', 'no', 'unknown', 'none', '']:
                is_positive = False
            
            if is_positive:
                positive_tests += 1
            else:
                negative_tests += 1
                
            # Determine if a match was predicted
            predicted_match_str = get_val(['predicted_match', 'top1_prediction', 'predicted_top1', 'top1_name'])
            is_predicted = True
            if predicted_match_str.lower() in ['false', '0', 'no', 'unknown', 'none', '']:
                is_predicted = False
                
            # Determine if the prediction was correct
            correct_val = get_val(['correct_identity', 'top1_correct', 'correct_top1'])
            is_correct = False
            if correct_val:
                is_correct = correct_val.lower() in ['true', '1', 'yes']
            else:
                actual_name = get_val(['actual_identity', 'true_identity', 'expected_match'])
                pred_name = get_val(['top1_prediction', 'predicted_top1', 'top1_name', 'predicted_match'])
                if actual_name and pred_name:
                    is_correct = actual_name.lower() == pred_name.lower()
                elif not is_positive and not is_predicted:
                    is_correct = True
            
            if is_correct:
                top1_correct_count += 1
                
            # Top-3 check
            top3_correct_val = get_val(['top3_correct', 'correct_top3'])
            if top3_correct_val:
                is_top3_correct = top3_correct_val.lower() in ['true', '1', 'yes']
            else:
                top3_str = get_val(['top3_predictions', 'top3', 'top3_names'])
                if top3_str:
                    if '|' in top3_str:
                        top3_list = [x.strip().lower() for x in top3_str.split('|')]
                    else:
                        top3_list = [x.strip().lower() for x in top3_str.split(',')]
                    actual_name = get_val(['actual_identity', 'true_identity', 'expected_match'])
                    is_top3_correct = actual_name.lower() in top3_list
                else:
                    is_top3_correct = is_correct
                    
            if is_top3_correct:
                top3_correct_count += 1
                
            # Classify TP, FP, FN, TN
            if is_positive:
                if is_predicted:
                    if is_correct:
                        tp += 1
                    else:
                        fp += 1
                else:
                    fn += 1
            else:
                if is_predicted:
                    fp += 1
                else:
                    tn += 1
                    
            # Search time
            time_str = get_val(['search_time', 'time'])
            if time_str:
                try:
                    total_search_time += float(time_str)
                    search_time_count += 1
                except ValueError:
                    pass
                      
    accuracy = (tp + tn) / total_tests if total_tests > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    top1_accuracy = top1_correct_count / total_tests if total_tests > 0 else 0.0
    top3_accuracy = top3_correct_count / total_tests if total_tests > 0 else 0.0
    
    false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    false_negative_rate = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    
    average_search_time = total_search_time / search_time_count if search_time_count > 0 else 0.0
    
    search_method = "PostgreSQL + FAISS Vector Search"
    if "faiss" not in csv_path.lower():
        search_method = "PostgreSQL + SQLite Cosine Fallback"
        
    return {
        "total_tests": total_tests,
        "positive_tests": positive_tests,
        "negative_tests": negative_tests,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1_score, 4),
        "top1_accuracy": round(top1_accuracy, 4),
        "top3_accuracy": round(top3_accuracy, 4),
        "false_positive_rate": round(false_positive_rate, 4),
        "false_negative_rate": round(false_negative_rate, 4),
        "average_search_time": round(average_search_time, 4),
        "dataset_name": "RMFRD / AFDB subset",
        "model": "FocusFace + ArcFace Ensemble",
        "search_method": search_method,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/evaluation")
async def get_evaluation():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(backend_dir, "evaluation_results.json")
    
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading JSON: {e}")
            
    parent_dir = os.path.dirname(backend_dir)
    csv_path = os.path.join(parent_dir, "rmfrd_faiss_results.csv")
    if not os.path.exists(csv_path):
        csv_path = os.path.join(parent_dir, "rmfrd_results.csv")
        
    if os.path.exists(csv_path):
        metrics = calculate_metrics_from_csv(csv_path)
        if metrics is not None:
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(metrics, f, indent=2)
            except Exception as e:
                print(f"Error writing JSON: {e}")
            return metrics
            
    raise HTTPException(
        status_code=404,
        detail="No evaluation results found. Run evaluation first or add rmfrd_faiss_results.csv."
    )

@app.post("/evaluation/run")
async def run_evaluation(role: str = Depends(require_role(["admin", "supervisor", "operator"]))):
    try:
        import sys
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.append(parent_dir)
            
        def run_eval_sync():
            try:
                import evaluate_rmfrd_faiss
                evaluate_rmfrd_faiss.evaluate()
                return True
            except Exception as e:
                print(f"Error running evaluate_rmfrd_faiss: {e}")
                try:
                    import evaluate_rmfrd
                    evaluate_rmfrd.evaluate()
                    return True
                except Exception as e2:
                    print(f"Error running evaluate_rmfrd: {e2}")
                    return False
                    
        await run_in_threadpool(run_eval_sync)
        
        csv_path = os.path.join(parent_dir, "rmfrd_faiss_results.csv")
        if not os.path.exists(csv_path):
            csv_path = os.path.join(parent_dir, "rmfrd_results.csv")
            
        if not os.path.exists(csv_path):
            raise HTTPException(
                status_code=404, 
                detail="Evaluation results CSV file not found. Make sure rmfrd_faiss_results.csv is in the project root."
            )
            
        metrics = calculate_metrics_from_csv(csv_path)
        if metrics is None:
            raise HTTPException(status_code=500, detail="Failed to calculate metrics from CSV.")
            
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(backend_dir, "evaluation_results.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
            
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AskRequest(BaseModel):
    question: str

@app.post("/rag/ask")
async def ask_assistant(request: AskRequest):
    try:
        # Fetch current database statistics, alerts, searches
        stats = db.get_stats()
        stats["recognition_model"] = "FocusFace + ArcFace Ensemble"
        stats["search_method"] = "PostgreSQL + FAISS Vector Search"
        
        alerts = db.get_alerts()
        searches = db.get_searches()
        
        # Fetch evaluation results from local cached JSON
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(backend_dir, "evaluation_results.json")
        eval_results = {}
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    eval_results = json.load(f)
            except Exception as e:
                print(f"Error reading evaluation results for RAG: {e}")
                
        # Build RAG knowledge base context chunks
        chunks = rag_engine.build_rag_context(stats, alerts, searches, eval_results)
        
        # Retrieve top relevant chunks based on word overlap
        selected_chunks, max_score = rag_engine.retrieve_relevant_chunks(request.question, chunks, top_k=5)
        
        # Generate final Synthesized Answer
        answer, sources = rag_engine.generate_rag_answer(
            request.question, 
            selected_chunks, 
            stats, 
            alerts, 
            searches, 
            eval_results
        )
        
        return {
            "answer": answer,
            "sources": sources
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/watchlist")
async def get_watchlist():
    try:
        return db.get_watchlist()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def get_health():
    try:
        try:
            db.get_stats()
            db_status = "connected"
        except Exception:
            db_status = "disconnected"
            
        try:
            from focusface_engine import get_ensemble_embedding
            model_status = "loaded"
        except Exception:
            model_status = "error"
            
        try:
            import faiss
            se_status = "FAISS active"
        except Exception:
            se_status = "Cosine fallback"
            
        db_type = "PostgreSQL" if db.USE_POSTGRES else "SQLite"
        
        return {
            "backend": "online",
            "database": db_status,
            "model": model_status,
            "search_engine": se_status,
            "database_type": db_type,
            "recognition_model": "FocusFace + ArcFace Ensemble",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))