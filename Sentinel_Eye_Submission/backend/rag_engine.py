import os
import re
import json

# Define common English stop words to filter out before keyword matching
STOP_WORDS = {
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd",
    'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers',
    'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which',
    'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if',
    'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
    'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out',
    'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
    'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
    'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should',
    "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't",
    'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't",
    'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't",
    'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't", 'tell'
}

def tokenize(text: str):
    """Tokenizes text and returns a set of lowercase words, excluding stop words."""
    words = re.findall(r'\b\w+\b', text.lower())
    return {w for w in words if w not in STOP_WORDS and len(w) > 1}

def load_project_knowledge():
    """Compiles static descriptions and definitions about the Sentinel Eye system."""
    knowledge = [
        {
            "id": "project_overview",
            "source": "Project Knowledge",
            "content": "Sentinel Eye is a biometric face search, watchlist matching, alert, and audit logging system. "
                       "It is designed to register target identities to a watchlist, query live surveillance captures, "
                       "raise alerts for watchlist hits, and maintain robust audit trails for security operators."
        },
        {
            "id": "model_architecture",
            "source": "Project Knowledge",
            "content": "The system utilizes a FocusFace + ArcFace Ensemble model for generating facial embeddings. "
                       "FocusFace is a specialised deep learning network designed to be robust to face masks, niqabs, "
                       "and heavy facial occlusions. ArcFace uses an additive angular margin loss to generate highly "
                       "discriminative 512-dimensional face embeddings."
        },
        {
            "id": "vector_search_faiss",
            "source": "Project Knowledge",
            "content": "FAISS (Facebook AI Similarity Search) is used for rapid, large-scale dense vector similarity search. "
                       "In Sentinel Eye, 512-dimensional face embeddings are queried using FAISS IndexFlatIP (Inner Product) "
                       "to find the top watchlist matches instantly."
        },
        {
            "id": "database_postgres",
            "source": "Project Knowledge",
            "content": "PostgreSQL serves as the primary relational database system, storing target metadata (names, passports, "
                       "DOB, watchlist tiers) and system logs. It uses the pgvector extension to perform native cosine similarity "
                       "vector search. If PostgreSQL is unavailable, the backend falls back to SQLite with NumPy-based cosine searches."
        },
        {
            "id": "matching_thresholds",
            "source": "Project Knowledge",
            "content": "Sentinel Eye operational matching thresholds: "
                       "- Normal Match Threshold: 0.45. "
                       "- Robust Match Threshold: 0.35. "
                       "- Strong Match Threshold: 0.60. "
                       "Alert level rules: "
                       "- Critical threat alert: score >= 0.80 (normal mode) or >= 0.75 (robust mode). "
                       "- Watchlist Warning: score >= 0.60 (normal mode) or >= 0.55 (robust mode). "
                       "- Low Possible Match: score >= 0.40. "
                       "- Unknown / No Match: score < 0.40 (not matched)."
        },
        {
            "id": "metrics_definitions_accuracy",
            "source": "Project Knowledge",
            "content": "Evaluation metrics definitions: "
                       "- Accuracy: Ratio of correct predictions (TP + TN) over total test cases. "
                       "- Precision: Ratio of true positives (TP) over all positive predictions (TP + FP). "
                       "- Recall: Ratio of true positives (TP) over all actual positive cases (TP + FN). "
                       "- F1-Score: Harmonic mean of precision and recall. "
                       "- Top-1 Accuracy: Percentage of test cases where the correct watchlist identity is the first-ranked candidate. "
                       "- Top-3 Accuracy: Percentage of test cases where the correct identity appears in the top 3 candidates."
        },
        {
            "id": "metrics_definitions_matrix",
            "source": "Project Knowledge",
            "content": "Confusion Matrix definitions in watchlist matching: "
                       "- True Positive (TP): An enrolled watchlist subject is correctly matched to their database identity. "
                       "- False Positive (FP): An unknown person is incorrectly matched to a watchlist target, OR a target is matched to the wrong identity. "
                       "- False Negative (FN): An enrolled target is not detected or is classified as unknown. "
                       "- True Negative (TN): An unknown person is correctly rejected and logged as unknown."
        }
    ]
    return knowledge

def build_rag_context(stats: dict, alerts: list, searches: list, evaluation_results: dict):
    """Converts current database statistics, alerts, searches, and evaluation results into context chunks."""
    chunks = load_project_knowledge()

    # Chunk: Current Database Stats
    stats_text = (
        f"Current Sentinel Eye System Stats: "
        f"Total enrolled watchlist target identities: {stats.get('total_users', 0)}. "
        f"Total biometric query checks performed: {stats.get('total_searches', 0)}. "
        f"Total threat alerts triggered: {stats.get('total_alerts', 0)}. "
        f"Active recognition model ensemble: {stats.get('recognition_model', 'FocusFace + ArcFace Ensemble')}. "
        f"Active database & vector indexing layer: {stats.get('search_method', 'PostgreSQL + FAISS')}. "
    )
    chunks.append({
        "id": "system_stats",
        "source": "Search Logs",
        "content": stats_text
    })

    # Chunk: Alerts Summary
    if alerts:
        alerts_desc = []
        critical_alerts = [a for a in alerts if a.get('alert_level') == 'critical']
        warning_alerts = [a for a in alerts if a.get('alert_level') == 'warning']
        
        # Find highest score in alerts
        highest_alert = max(alerts, key=lambda x: x.get('score', 0)) if alerts else None
        highest_str = f"Highest alert score is {highest_alert.get('score') * 100:.2f}% for {highest_alert.get('name')} on {highest_alert.get('camera')}." if highest_alert else ""
        
        alerts_desc.append(f"System Watchlist Alerts Summary: Total active alerts = {len(alerts)}. "
                           f"Critical threat level alerts = {len(critical_alerts)}. "
                           f"Warning level alerts = {len(warning_alerts)}. {highest_str}")
        
        # Add details of recent 3 alerts
        recent_alerts = alerts[:3]
        for a in recent_alerts:
            alerts_desc.append(
                f"Alert details: Subject {a.get('name')} triggered a {a.get('alert_level')} alert on {a.get('camera')} "
                f"at {a.get('created_at')} with a match score of {a.get('score') * 100:.2f}%. Current status is {a.get('status')}."
            )
        
        chunks.append({
            "id": "system_alerts",
            "source": "Alerts",
            "content": " ".join(alerts_desc)
        })
    else:
        chunks.append({
            "id": "system_alerts",
            "source": "Alerts",
            "content": "System Watchlist Alerts Summary: No watchlist alerts have been generated in the system yet."
        })

    # Chunk: Audit Logs Summary
    if searches:
        searches_desc = [f"Surveillance Audit Logs: Total logs count is {len(searches)}."]
        matches = [s for s in searches if s.get('status') == 'match']
        searches_desc.append(f"Total matched queries count = {len(matches)}. Total unknown/rejected queries count = {len(searches) - len(matches)}.")
        
        # Add details of recent 3 searches
        recent_searches = searches[:3]
        for s in recent_searches:
            searches_desc.append(
                f"Audit trail: Query for {s.get('best_match')} logged at {s.get('created_at')} on {s.get('camera')} "
                f"with best match score {s.get('score') * 100:.2f}%. Status was {s.get('status')}."
            )
        
        chunks.append({
            "id": "system_searches",
            "source": "Search Logs",
            "content": " ".join(searches_desc)
        })
    else:
        chunks.append({
            "id": "system_searches",
            "source": "Search Logs",
            "content": "Surveillance Audit Logs: No search logs or audit trails are available in the system yet."
        })

    # Chunk: Evaluation Results Summary
    if evaluation_results:
        eval_text = (
            f"Watchlist Model Evaluation Results summary: "
            f"Total evaluated test images: {evaluation_results.get('total_tests', 0)}. "
            f"Positive test images: {evaluation_results.get('positive_tests', 0)}. "
            f"Negative test images: {evaluation_results.get('negative_tests', 0)}. "
            f"Top-1 Accuracy: {evaluation_results.get('top1_accuracy', 0) * 100:.2f}%. "
            f"Top-3 Accuracy: {evaluation_results.get('top3_accuracy', 0) * 100:.2f}%. "
            f"Overall system accuracy: {evaluation_results.get('accuracy', 0) * 100:.2f}%. "
            f"Precision metric: {evaluation_results.get('precision', 0) * 100:.2f}%. "
            f"Recall metric: {evaluation_results.get('recall', 0) * 100:.2f}%. "
            f"F1-Score metric: {evaluation_results.get('f1_score', 0) * 100:.2f}%. "
            f"False Positive Rate (FPR): {evaluation_results.get('false_positive_rate', 0) * 100:.2f}%. "
            f"False Negative Rate (FNR): {evaluation_results.get('false_negative_rate', 0) * 100:.2f}%. "
            f"Confusion matrix metrics: TP={evaluation_results.get('tp', 0)}, FP={evaluation_results.get('fp', 0)}, "
            f"FN={evaluation_results.get('fn', 0)}, TN={evaluation_results.get('tn', 0)}. "
            f"Average facial search time: {evaluation_results.get('average_search_time', 0.0):.4f} seconds. "
            f"Evaluation dataset name: {evaluation_results.get('dataset_name', 'RMFRD / AFDB subset')}. "
            f"Last evaluation update: {evaluation_results.get('last_updated', 'N/A')}."
        )
        chunks.append({
            "id": "evaluation_results",
            "source": "Evaluation Results",
            "content": eval_text
        })
    else:
        chunks.append({
            "id": "evaluation_results",
            "source": "Evaluation Results",
            "content": "Watchlist Model Evaluation Results: No evaluation results are available yet. "
                       "Run evaluation first to populate metrics."
        })

    return chunks

def retrieve_relevant_chunks(question: str, chunks: list, top_k: int = 5):
    """Retrieves the top_k most relevant chunks using word overlap scoring."""
    q_tokens = tokenize(question)
    
    if not q_tokens:
        return [], 0
        
    scored_chunks = []
    max_score = 0
    
    for chunk in chunks:
        c_tokens = tokenize(chunk["content"])
        # Score is simply the count of overlapping tokens
        score = len(q_tokens.intersection(c_tokens))
        
        # Boost score slightly if chunk id is related to query keywords
        boost = 0
        for token in q_tokens:
            if token in chunk["id"]:
                boost += 1
        score += boost
        
        if score > max_score:
            max_score = score
            
        scored_chunks.append((score, chunk))
        
    # Sort descending by score
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # Return top_k chunks that have at least some keyword overlap (score > 0)
    selected = [chunk for score, chunk in scored_chunks[:top_k] if score > 0]
    return selected, max_score

def generate_rag_answer(question: str, selected_chunks: list, stats: dict, alerts: list, searches: list, evaluation_results: dict):
    """Generates a professional, rule-based answer based on query keywords and selected chunks context."""
    q_lower = question.lower()
    
    # Handle out of domain / unrelated questions
    all_keywords = ["sentinel", "eye", "focusface", "arcface", "faiss", "postgres", "sqlite", "alert", "alerts", 
                    "log", "logs", "search", "searches", "audit", "evaluation", "results", "accuracy", "precision", 
                    "recall", "f1", "top-1", "top-3", "tp", "fp", "fn", "tn", "confusion", "threshold", "thresholds", 
                    "score", "watchlist", "system", "architect", "working", "work", "biometric", "face"]
    
    is_related = any(kw in q_lower for kw in all_keywords)
    if not is_related or not selected_chunks:
        return (
            "I can answer questions about Sentinel Eye, alerts, audit logs, evaluation metrics, and project architecture.",
            ["Project Knowledge"]
        )
        
    # Synthesize answers based on semantic intent
    sources = list({chunk["source"] for chunk in selected_chunks})
    
    # Intent 1: Project overview
    if "what is sentinel eye" in q_lower or "project overview" in q_lower:
        ans = (
            "**Sentinel Eye** is a state-of-the-art biometric face search, watchlist matching, alert, and audit logging system. "
            "It is designed to secure high-security points (such as airports, border control, or restricted facilities). "
            "The system allows admins and supervisors to enroll targets of interest into a watchlist, queries live surveillance feeds "
            "against this watchlist, triggers real-time visual alerts for verified matches, and maintains an immutable audit log trail of all checks."
        )
        return ans, ["Project Knowledge"]
        
    # Intent 2: Model and Face Embeddings (FocusFace + ArcFace)
    elif "focusface" in q_lower or "arcface" in q_lower or "ensemble" in q_lower or "embeddings" in q_lower:
        ans = (
            "Sentinel Eye uses a **FocusFace + ArcFace Ensemble** model to extract facial embeddings:\n\n"
            "1. **FocusFace** is a specialized deep neural network optimized to handle heavily occluded faces (such as subjects wearing medical masks, face coverings, or niqabs).\n"
            "2. **ArcFace** uses an Additive Angular Margin Loss function to generate high-precision, discriminative 512-dimensional dense feature vectors (embeddings).\n\n"
            "Combining these models into an ensemble allows the system to remain highly robust in real-world environments with varying lighting, disguises, and angles."
        )
        return ans, ["Project Knowledge"]
        
    # Intent 3: FAISS role
    elif "faiss" in q_lower:
        ans = (
            "**FAISS** (Facebook AI Similarity Search) is integrated as the high-performance vector indexing and search engine layer. "
            "Once face captures are converted into 512-dimensional embeddings, FAISS queries them against the enrolled watchlist targets. "
            "By utilizing an `IndexFlatIP` (Inner Product / Cosine similarity search), FAISS identifies candidate matches in milliseconds, making it highly scalable."
        )
        return ans, ["Project Knowledge"]
        
    # Intent 4: PostgreSQL role
    elif "postgres" in q_lower or "postgresql" in q_lower or "pgvector" in q_lower:
        ans = (
            "**PostgreSQL** is the core relational database used to store identity details (target name, date of birth, passport numbers, watchlist tiers) and audit trails. "
            "It integrates the **pgvector** extension to perform native vector operations directly within database queries using HNSW indexing. "
            "If PostgreSQL is not running or fails to connect, the system automatically falls back to an SQLite local file with NumPy cosine calculation."
        )
        return ans, ["Project Knowledge"]
        
    # Intent 5: Thresholds and levels
    elif "threshold" in q_lower or "match score" in q_lower or "alert level" in q_lower:
        ans = (
            "Sentinel Eye matches faces using cosine similarity scores and triggers alerts based on standard thresholds:\n"
            "- **Normal Match Threshold**: 0.45. Any score above this counts as a verified match.\n"
            "- **Robust Match Threshold**: 0.35. Lower threshold activated when scanning heavily disguised, low-quality, or niqab-covered captures.\n"
            "- **Strong Match Threshold**: 0.60. Requires high-confidence matching.\n\n"
            "**Alert Threat Levels**:\n"
            "- 🚨 **Critical**: Score >= 0.80 (normal) or >= 0.75 (robust mode). Requires immediate checkpoint notification.\n"
            "- ⚠ **Warning**: Score >= 0.60 (normal) or >= 0.55 (robust mode). Triggers watchlist warning alert.\n"
            "- ℹ **Low**: Score >= 0.40. Logged as possible match."
        )
        return ans, ["Project Knowledge"]
        
    # Intent 6: TP, FP, FN, TN
    elif "tp" in q_lower or "fp" in q_lower or "fn" in q_lower or "tn" in q_lower or "confusion matrix" in q_lower:
        eval_part = ""
        if evaluation_results:
            eval_part = (
                f"\n\n**Current Confusion Matrix Values**:\n"
                f"- **True Positive (TP)**: {evaluation_results.get('tp', 0)} (correct watchlist match)\n"
                f"- **False Positive (FP)**: {evaluation_results.get('fp', 0)} (unknown person matched incorrectly)\n"
                f"- **False Negative (FN)**: {evaluation_results.get('fn', 0)} (watchlist target missed)\n"
                f"- **True Negative (TN)**: {evaluation_results.get('tn', 0)} (correctly rejected unknown)"
            )
        ans = (
            "In biometric watchlist matching, the confusion matrix elements are defined as:\n"
            "1. **TP (True Positive)**: Enrolled person is correctly detected and matched to their database identity.\n"
            "2. **FP (False Positive)**: Unknown or wrong person is incorrectly matched to an enrolled target.\n"
            "3. **FN (False Negative)**: Enrolled target is not detected by the system, or matched to 'Unknown'.\n"
            "4. **TN (True Negative)**: An unknown (non-enrolled) person is correctly rejected by the system."
            + eval_part
        )
        return ans, ["Project Knowledge", "Evaluation Results"] if evaluation_results else ["Project Knowledge"]
        
    # Intent 7: Explain evaluation results
    elif "evaluation results" in q_lower or "accuracy" in q_lower or "recall" in q_lower or "precision" in q_lower or "f1" in q_lower or "top-1" in q_lower or "top-3" in q_lower:
        if evaluation_results:
            ans = (
                f"### Watchlist Evaluation Metrics Summary\n"
                f"Here are the latest computed metrics for the Sentinel Eye model:\n\n"
                f"- **Total Test Images**: {evaluation_results.get('total_tests', 0)}\n"
                f"- **Overall Model Accuracy**: {evaluation_results.get('accuracy', 0) * 100:.2f}%\n"
                f"- **Precision (Watchlist Hit Accuracy)**: {evaluation_results.get('precision', 0) * 100:.2f}%\n"
                f"- **Recall (Watchlist Catch Rate)**: {evaluation_results.get('recall', 0) * 100:.2f}%\n"
                f"- **F1-Score**: {evaluation_results.get('f1_score', 0) * 100:.2f}%\n"
                f"- **Top-1 Accuracy**: {evaluation_results.get('top1_accuracy', 0) * 100:.2f}% (Correct identity is first candidate)\n"
                f"- **Top-3 Accuracy**: {evaluation_results.get('top3_accuracy', 0) * 100:.2f}% (Correct identity in top 3 candidates)\n"
                f"- **False Positive Rate (FPR)**: {evaluation_results.get('false_positive_rate', 0) * 100:.2f}%\n"
                f"- **False Negative Rate (FNR)**: {evaluation_results.get('false_negative_rate', 0) * 100:.2f}%\n"
                f"- **Average Search Query Time**: {evaluation_results.get('average_search_time', 0.0):.4f} seconds.\n\n"
                f"**Dataset details**: Tested on '{evaluation_results.get('dataset_name', 'RMFRD / AFDB subset')}' using {evaluation_results.get('search_method', 'PostgreSQL + FAISS Vector Search')}."
            )
            return ans, ["Evaluation Results"]
        else:
            return (
                "No evaluation results have been computed yet. Please run evaluation in the dashboard to check model accuracy metrics.",
                ["Evaluation Results"]
            )
            
    # Intent 8: Summarize latest alerts
    elif "summarize latest alerts" in q_lower or "alerts" in q_lower or "alert count" in q_lower:
        if alerts:
            critical_alerts = [a for a in alerts if a.get('alert_level') == 'critical']
            warning_alerts = [a for a in alerts if a.get('alert_level') == 'warning']
            highest_alert = max(alerts, key=lambda x: x.get('score', 0)) if alerts else None
            
            # Details of top 3
            details = []
            for i, a in enumerate(alerts[:3]):
                details.append(f"{i+1}. **{a.get('name')}**: Score {a.get('score') * 100:.2f}%, Level: {a.get('alert_level')} on {a.get('camera')} at {a.get('created_at')}")
                
            ans = (
                f"### Active Watchlist Alerts Summary\n"
                f"There are currently **{len(alerts)} active alerts** in the database:\n"
                f"- 🚨 **Critical alerts**: {len(critical_alerts)}\n"
                f"- ⚠ **Warning alerts**: {len(warning_alerts)}\n\n"
                f"**Most recent alerts details**:\n" + "\n".join(details) + "\n\n"
                f"The highest score record belongs to **{highest_alert.get('name')}** with **{highest_alert.get('score') * 100:.2f}%** matching score."
            )
            return ans, ["Alerts"]
        else:
            return (
                "There are currently no active watchlist alerts recorded in the system.",
                ["Alerts"]
            )
            
    # Intent 9: Who had highest score
    elif "highest match score" in q_lower or "highest score" in q_lower or "best score" in q_lower or "max score" in q_lower:
        highest_record = None
        record_source = ""
        
        # Look in alerts
        if alerts:
            highest_a = max(alerts, key=lambda x: x.get('score', 0))
            highest_record = {"name": highest_a.get('name'), "score": highest_a.get('score'), "camera": highest_a.get('camera'), "time": highest_a.get('created_at')}
            record_source = "Alerts"
            
        # Look in searches/audit logs
        if searches:
            highest_s = max(searches, key=lambda x: x.get('score', 0))
            if highest_record is None or highest_s.get('score', 0) > highest_record["score"]:
                highest_record = {"name": highest_s.get('best_match'), "score": highest_s.get('score'), "camera": highest_s.get('camera'), "time": highest_s.get('created_at')}
                record_source = "Search Logs"
                
        if highest_record:
            ans = (
                f"The highest match score in the system is **{highest_record['score'] * 100:.2f}%**.\n"
                f"This matches subject **{highest_record['name']}** on **{highest_record['camera']}** "
                f"recorded at **{highest_record['time']}**. "
                f"This check was logged in **{record_source}**."
            )
            return ans, [record_source]
        else:
            return (
                "No biometric checks or watchlist matches have been recorded yet. Embeddings database is empty.",
                ["Search Logs"]
            )
            
    # Intent 10: Audit logs / searches summary
    elif "audit logs" in q_lower or "audit log" in q_lower or "searches" in q_lower or "audit trail" in q_lower:
        if searches:
            matches = [s for s in searches if s.get('status') == 'match']
            details = []
            for i, s in enumerate(searches[:3]):
                details.append(f"{i+1}. Query: **{s.get('best_match')}** (Score: {s.get('score') * 100:.2f}%) on {s.get('camera')} at {s.get('created_at')}")
                
            ans = (
                f"### Surveillance Audit Logs Summary\n"
                f"A total of **{len(searches)} queries** have been recorded in the surveillance audit log trail:\n"
                f"- **Confirmed Matches**: {len(matches)}\n"
                f"- **Unknown/Rejections**: {len(searches) - len(matches)}\n\n"
                f"**Most recent audit trail records**:\n" + "\n".join(details)
            )
            return ans, ["Search Logs"]
        else:
            return (
                "The surveillance audit log is empty. No query scans have been conducted yet.",
                ["Search Logs"]
            )
            
    # Fallback to dynamic summary based on selected chunks
    context_blocks = []
    for chunk in selected_chunks:
        context_blocks.append(f"From {chunk['source']}: {chunk['content']}")
        
    ans = (
        "Here is the relevant information I retrieved about your query:\n\n" + 
        "\n\n".join(context_blocks)
    )
    return ans, sources
