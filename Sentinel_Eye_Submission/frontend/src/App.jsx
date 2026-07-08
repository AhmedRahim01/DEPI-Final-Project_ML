import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const getErrorMessage = (data, fallback = "Request failed.") => {
  if (!data) return fallback;

  if (typeof data === "string") return data;

  if (typeof data.detail === "string") return data.detail;

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((err) => {
        const field = err.loc ? err.loc.join(" → ") : "field";
        return `${field}: ${err.msg}`;
      })
      .join(" | ");
  }

  if (typeof data.detail === "object" && data.detail !== null) {
    return JSON.stringify(data.detail);
  }

  if (typeof data.message === "string") return data.message;

  return fallback;
};

function App() {
  // Authentication Role State
  const [activeRole, setActiveRole] = useState("admin");

  // Registration Form States
  const [name, setName] = useState("");
  const [nationality, setNationality] = useState("Egypt");
  const [dob, setDob] = useState("1995-01-01");
  const [passportNumber, setPassportNumber] = useState("EG1234567");
  const [watchlistTier, setWatchlistTier] = useState(3); // 1 = Red Notice, 2 = Suspected, 3 = POI
  const [enrollmentSite, setEnrollmentSite] = useState("Cairo International Airport");
  const [registerFile, setRegisterFile] = useState(null);

  // Surveillance Form States
  const [recognizeFile, setRecognizeFile] = useState(null);
  const [robustMode, setRobustMode] = useState(false);
  const [camera, setCamera] = useState("Camera 1 - Main Gate");

  // Output States
  const [registerMessage, setRegisterMessage] = useState("");
  const [registerError, setRegisterError] = useState(false);
  const [result, setResult] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [searches, setSearches] = useState([]);

  const [stats, setStats] = useState({
    total_users: 0,
    total_alerts: 0,
    total_searches: 0,
    recognition_model: "FocusFace + ArcFace Ensemble",
    search_method: "PostgreSQL + FAISS",
  });

  const [loadingRegister, setLoadingRegister] = useState(false);
  const [loadingRecognize, setLoadingRecognize] = useState(false);

  // Evaluation States
  const [evaluationData, setEvaluationData] = useState(null);
  const [loadingEvaluation, setLoadingEvaluation] = useState(false);
  const [evaluationError, setEvaluationError] = useState("");

  // RAG Assistant States
  const [ragQuestion, setRagQuestion] = useState("");
  const [ragAnswer, setRagAnswer] = useState("");
  const [ragSources, setRagSources] = useState([]);
  const [loadingRag, setLoadingRag] = useState(false);
  const [ragError, setRagError] = useState("");

  // Watchlist Management States
  const [watchlist, setWatchlist] = useState([]);
  const [loadingWatchlist, setLoadingWatchlist] = useState(false);
  const [watchlistError, setWatchlistError] = useState("");

  // Bulk Enrollment States
  const [bulkTargets, setBulkTargets] = useState([]);
  const [loadingBulk, setLoadingBulk] = useState(false);
  const [bulkMessage, setBulkMessage] = useState("");
  const [bulkError, setBulkError] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);

  const formatScore = (score) => {
    if (score === undefined || score === null) return "0%";

    const numericScore = Number(score);

    if (Number.isNaN(numericScore)) return "0%";

    if (numericScore <= 1) {
      return `${(numericScore * 100).toFixed(2)}%`;
    }

    return `${numericScore.toFixed(2)}%`;
  };

  const getResultTitle = () => {
    if (!result) return "";
    if (!result.match) return "No Confirmed Match";

    if (result.alert_level === "critical") return "🚨 Critical Match Detected";
    if (result.alert_level === "warning") return "⚠ Watchlist Warning";
    if (result.alert_level === "low") return "Low Possible Match";

    return "Match Identified";
  };

  const getWatchlistTierLabel = (tier) => {
    if (tier === 1) return "Red Notice (Critical)";
    if (tier === 2) return "Suspected HVT (High)";
    if (tier === 3) return "POI (Medium)";
    return "Normal Watchlist";
  };

  const getWatchlistTierBadge = (tier) => {
    if (tier === 1) return <span className="badge badge-red">Red Notice</span>;
    if (tier === 2) return <span className="badge badge-orange">Suspected HVT</span>;
    if (tier === 3) return <span className="badge badge-yellow">POI</span>;
    return <span className="badge badge-blue">Normal</span>;
  };

  const getResultThreatClass = () => {
    if (!result) return "";
    if (!result.match) return "threat-none";
    if (result.alert_level === "critical") return "threat-critical";
    if (result.alert_level === "warning") return "threat-warning";
    if (result.alert_level === "low") return "threat-low";
    return "threat-none";
  };

  // Helper to attach authorization header based on role
  const getAuthHeaders = () => {
    return {
      Authorization: `Bearer token-${activeRole}`,
    };
  };

  const fetchWatchlist = async () => {
    setLoadingWatchlist(true);
    setWatchlistError("");
    try {
      const res = await fetch(`${API_URL}/watchlist`);
      const data = await res.json();
      if (!res.ok) {
        throw new Error(getErrorMessage(data, "Failed to load watchlist."));
      }
      setWatchlist(data);
    } catch (error) {
      console.error("Watchlist load error:", error);
      setWatchlistError(error.message || "Failed to load watchlist.");
    } finally {
      setLoadingWatchlist(false);
    }
  };

  const cleanFilename = (filename) => {
    const withoutExt = filename.substring(0, filename.lastIndexOf('.')) || filename;
    const clean = withoutExt.replace(/[_-]/g, " ").trim();
    return clean.split(/\s+/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
  };

  const handleBulkFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);

    const targets = selectedFiles.map(file => ({
      file: file,
      filename: file.name,
      name: cleanFilename(file.name),
      nationality: "Egypt",
      dob: "1995-01-01",
      passport_number: "EG1234567",
      watchlist_tier: 3,
      enrollment_site: "Cairo International Airport",
      status: "idle",
      errorDetail: ""
    }));

    setBulkTargets(targets);
    setBulkMessage("");
    setBulkResult(null);
  };

  const handleBulkTargetChange = (index, field, value) => {
    const updated = [...bulkTargets];
    updated[index] = { ...updated[index], [field]: value };
    setBulkTargets(updated);
  };

  const handleBulkEnroll = async (e) => {
    e.preventDefault();
    if (bulkTargets.length === 0) {
      setBulkMessage("No targets selected for bulk enrollment.");
      setBulkError(true);
      setBulkResult(null);
      return;
    }

    setLoadingBulk(true);
    setBulkMessage("");
    setBulkError(false);
    setBulkResult(null);

    let successCount = 0;
    let failedCount = 0;
    const rowResults = [];

    const updatedTargets = [...bulkTargets];

    for (let i = 0; i < updatedTargets.length; i++) {
      const target = updatedTargets[i];

      updatedTargets[i] = { ...target, status: "pending", errorDetail: "" };
      setBulkTargets([...updatedTargets]);

      try {
        const formData = new FormData();
        formData.append("name", target.name.trim());
        formData.append("nationality", target.nationality.trim());
        formData.append("dob", target.dob.trim());
        formData.append("passport_number", target.passport_number.trim());
        formData.append("watchlist_tier", target.watchlist_tier);
        formData.append("enrollment_site", target.enrollment_site.trim());
        formData.append("files", target.file);

        const res = await fetch(`${API_URL}/register`, {
          method: "POST",
          headers: getAuthHeaders(),
          body: formData,
        });

        const data = await res.json();

        if (!res.ok) {
          throw new Error(getErrorMessage(data, "Enrollment failed."));
        }

        updatedTargets[i] = { ...target, status: "success" };
        successCount++;
        rowResults.push({ filename: target.filename, status: "success", name: target.name });
      } catch (err) {
        console.error(`Error enrolling ${target.filename}:`, err);
        updatedTargets[i] = { ...target, status: "error", errorDetail: err.message || "Failed" };
        failedCount++;
        rowResults.push({ filename: target.filename, status: "failed", detail: err.message || "Failed" });
      }

      setBulkTargets([...updatedTargets]);
    }

    setLoadingBulk(false);

    await loadDashboard();
    await fetchWatchlist();

    setBulkResult({
      success_count: successCount,
      total_count: updatedTargets.length,
      results: rowResults
    });

    if (failedCount === 0) {
      setBulkMessage(`Successfully enrolled all ${successCount} targets!`);
      setBulkError(false);
      setBulkTargets([]);
      const fileInput = document.getElementById("bulk-files-input");
      if (fileInput) fileInput.value = "";
    } else {
      setBulkMessage(`Processed: ${successCount} succeeded, ${failedCount} failed.`);
      setBulkError(true);
    }
  };

  const fetchEvaluation = async () => {
    try {
      setEvaluationError("");
      const res = await fetch(`${API_URL}/evaluation`);
      if (!res.ok) {
        if (res.status === 404) {
          setEvaluationData(null);
          return;
        }
        const data = await res.json();
        throw new Error(getErrorMessage(data, "Failed to load evaluation."));
      }
      const data = await res.json();
      setEvaluationData(data);
    } catch (error) {
      console.error("Evaluation load error:", error);
      setEvaluationError(error.message || "Failed to load evaluation.");
    }
  };

  const loadDashboard = async () => {
    try {
      const statsRes = await fetch(`${API_URL}/stats`);
      const statsData = await statsRes.json();
      setStats(statsData);

      const alertsRes = await fetch(`${API_URL}/alerts`);
      const alertsData = await alertsRes.json();
      setAlerts(alertsData);

      const searchesRes = await fetch(`${API_URL}/searches`);
      const searchesData = await searchesRes.json();
      setSearches(searchesData);
    } catch (error) {
      console.error("Dashboard load error:", error);
    }
  };

  useEffect(() => {
    loadDashboard();
    fetchEvaluation();
    fetchWatchlist();
  }, []);

  const handleRunEvaluation = async () => {
    setLoadingEvaluation(true);
    setEvaluationError("");
    try {
      const res = await fetch(`${API_URL}/evaluation/run`, {
        method: "POST",
        headers: getAuthHeaders(),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(getErrorMessage(data, "Evaluation run failed."));
      }
      setEvaluationData(data);
      await loadDashboard();
    } catch (error) {
      setEvaluationError(error.message || "Failed to run evaluation.");
    } finally {
      setLoadingEvaluation(false);
    }
  };

  const handleAskRag = async (e, customQuestion = null) => {
    if (e) e.preventDefault();
    const query = customQuestion !== null ? customQuestion : ragQuestion;
    if (!query || !query.trim()) return;

    setLoadingRag(true);
    setRagError("");
    setRagAnswer("");
    setRagSources([]);

    if (customQuestion !== null) {
      setRagQuestion(customQuestion);
    }

    try {
      const res = await fetch(`${API_URL}/rag/ask`, {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: query }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(getErrorMessage(data, "Assistant failed to generate response."));
      }

      setRagAnswer(data.answer);
      setRagSources(data.sources || []);
    } catch (error) {
      console.error("RAG Query error:", error);
      setRagError(error.message || "Failed to ask assistant.");
    } finally {
      setLoadingRag(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();

    if (!name || !registerFile) {
      setRegisterMessage("Please enter name and select a facial image.");
      setRegisterError(true);
      return;
    }

    setLoadingRegister(true);
    setRegisterMessage("");
    setRegisterError(false);

    try {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("nationality", nationality);
      formData.append("dob", dob);
      formData.append("passport_number", passportNumber);
      formData.append("watchlist_tier", watchlistTier);
      formData.append("enrollment_site", enrollmentSite);
      formData.append("files", registerFile);

      const res = await fetch(`${API_URL}/register`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(getErrorMessage(data, "Registration failed."));
      }

      setRegisterMessage(
        `Success: ${data.message || "Identity enrolled successfully"} (${data.name || name})`
      );
      setRegisterError(false);
      setName("");
      setRegisterFile(null);

      await loadDashboard();
      await fetchWatchlist();
    } catch (error) {
      setRegisterMessage(error.message || "Registration failed.");
      setRegisterError(true);
    } finally {
      setLoadingRegister(false);
    }
  };

  const handleRecognize = async (e) => {
    e.preventDefault();

    if (!recognizeFile) {
      setResult({
        match: false,
        name: "No image selected",
        score: 0,
        confidence: "none",
      });
      return;
    }

    setLoadingRecognize(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", recognizeFile);
      formData.append("robust_mode", robustMode);
      formData.append("camera", camera);

      const res = await fetch(`${API_URL}/recognize`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(getErrorMessage(data, "Recognition failed."));
      }

      setResult(data);
      await loadDashboard();
    } catch (error) {
      setResult({
        match: false,
        name: "Error",
        score: 0,
        confidence: "none",
        error: error.message || "Recognition failed.",
      });
    } finally {
      setLoadingRecognize(false);
    }
  };

  return (
    <div className="page">
      <header className="hero">
        <div>
          <h1>Sentinel Eye</h1>
          <p>Biometric Face Search, Watchlist Matching & Alert System</p>
        </div>

        {/* Simulated Role-Based Access Control Switcher */}
        <div className="role-panel">
          <span>Active Role:</span>
          <div className="role-switcher">
            <button
              className={`role-btn ${activeRole === "admin" ? "active" : ""}`}
              onClick={() => setActiveRole("admin")}
            >
              Admin
            </button>
            <button
              className={`role-btn ${activeRole === "supervisor" ? "active" : ""}`}
              onClick={() => setActiveRole("supervisor")}
            >
              Supervisor
            </button>
            <button
              className={`role-btn ${activeRole === "operator" ? "active" : ""}`}
              onClick={() => setActiveRole("operator")}
            >
              Operator
            </button>
          </div>
        </div>
      </header>

      {/* Stats Dashboard Grid */}
      <section className="dashboard">
        <div className="card stat-card">
          <h3>Watchlist Identities</h3>
          <p>{stats.total_users}</p>
        </div>

        <div className="card stat-card">
          <h3>Total Checks</h3>
          <p>{stats.total_searches}</p>
        </div>

        <div className="card stat-card">
          <h3>Threat Alerts</h3>
          <p>{stats.total_alerts}</p>
        </div>

        <div className="card stat-card">
          <h3>Engine Backend</h3>
          <p style={{ fontSize: "16px", marginTop: "24px", fontWeight: "600" }}>
            Model: <span style={{ color: "var(--cyan)" }}>{stats.recognition_model}</span>
            <br />
            DB Layer: <span style={{ color: "var(--purple)" }}>{stats.search_method}</span>
          </p>
        </div>
      </section>

      {/* Forms Section */}
      <main className="grid">
        {/* Watchlist Registration Card */}
        <section className="card">
          <h2>Biometric Enrollment</h2>
          <p className="muted">Register new watchlist targets. (Requires Admin/Supervisor permissions).</p>

          <form onSubmit={handleRegister}>
            <div className="form-group-row">
              <div>
                <label>Target Name</label>
                <input
                  type="text"
                  placeholder="Enter full name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div>
                <label>Nationality</label>
                <input
                  type="text"
                  placeholder="Enter nationality"
                  value={nationality}
                  onChange={(e) => setNationality(e.target.value)}
                />
              </div>
            </div>

            <div className="form-group-row">
              <div>
                <label>Date of Birth</label>
                <input type="date" value={dob} onChange={(e) => setDob(e.target.value)} />
              </div>
              <div>
                <label>Passport Number</label>
                <input
                  type="text"
                  placeholder="Passport code"
                  value={passportNumber}
                  onChange={(e) => setPassportNumber(e.target.value)}
                />
              </div>
            </div>

            <div className="form-group-row">
              <div>
                <label>Watchlist Tier</label>
                <select value={watchlistTier} onChange={(e) => setWatchlistTier(parseInt(e.target.value))}>
                  <option value={1}>Red Notice (Critical)</option>
                  <option value={2}>Suspected (High)</option>
                  <option value={3}>POI (Medium)</option>
                </select>
              </div>
              <div>
                <label>Enrollment Site</label>
                <input type="text" value={enrollmentSite} onChange={(e) => setEnrollmentSite(e.target.value)} />
              </div>
            </div>

            <label>Facial Scan Image</label>
            <input type="file" accept="image/*" onChange={(e) => setRegisterFile(e.target.files[0])} />

            <button type="submit" disabled={loadingRegister}>
              {loadingRegister ? "Processing Biometrics..." : "Enroll Subject to Watchlist"}
            </button>
          </form>

          {registerMessage && <div className={`message ${registerError ? "error" : ""}`}>{registerMessage}</div>}

        </section>

        {/* Surveillance Search check card */}
        <section className="card">
          <h2>Surveillance Feed Matcher</h2>
          <p className="muted">Search live captures against database (accessible to all operators).</p>

          <form onSubmit={handleRecognize}>
            <label>Live Capture File</label>
            <input type="file" accept="image/*" onChange={(e) => setRecognizeFile(e.target.files[0])} />

            <label>Capture Feed Origin</label>
            <select value={camera} onChange={(e) => setCamera(e.target.value)}>
              <option>Camera 1 - Main Gate</option>
              <option>Camera 2 - Arrivals Hall</option>
              <option>Camera 3 - Passport Control</option>
              <option>Camera 4 - VIP Lounge</option>
            </select>

            <div className="checkbox-row">
              <input type="checkbox" checked={robustMode} onChange={(e) => setRobustMode(e.target.checked)} />
              <span>Activate robust matching mode (low quality / disguised / niqab)</span>
            </div>

            <button type="submit" disabled={loadingRecognize}>
              {loadingRecognize ? "Comparing Biometrics..." : "Verify Capture"}
            </button>
          </form>

          {result && (
            <div className={`result ${getResultThreatClass()}`}>
              <div className="result-header">
                <h3>{getResultTitle()}</h3>
                {result.match && getWatchlistTierBadge(result.watchlist_tier)}
              </div>

              {result.match ? (
                <div className="profile-card">
                  <div className="profile-header">
                    <span className="profile-name">{result.name}</span>
                  </div>

                  <div className="profile-details-grid">
                    <div className="profile-detail">
                      <span>Nationality</span>
                      <span>{result.nationality || "Not specified"}</span>
                    </div>

                    <div className="profile-detail">
                      <span>Passport Code</span>
                      <span>{result.passport_number || "Not specified"}</span>
                    </div>

                    <div className="profile-detail">
                      <span>Date of Birth</span>
                      <span>{result.dob || "Not specified"}</span>
                    </div>

                    <div className="profile-detail">
                      <span>Alert Match Score</span>
                      <span style={{ color: "var(--cyan)" }}>{formatScore(result.score)}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <p>No matches exceeded the confidence threshold in the watchlist database.</p>
              )}

              {result.error && (
                <p className="message error">
                  <strong>Access Error:</strong> {result.error}
                </p>
              )}

              {result.match && result.alert_level === "critical" && (
                <div className="alert-box">
                  🚨 CRITICAL THREAT DETECTED: Notify check-point officers and supervisor immediately!
                </div>
              )}

              {result.top_matches && result.top_matches.length > 0 && (
                <div className="top-matches">
                  <h4>Ranked Candidate Matches</h4>
                  {result.top_matches.map((item, index) => (
                    <div key={index} className="match-row">
                      <span>
                        {index + 1}. {item.name} ({getWatchlistTierLabel(item.watchlist_tier)})
                      </span>
                      <span>{formatScore(item.score)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </main>

      {/* Bulk Watchlist Enrollment Section */}
      <section className="grid-full bulk-enrollment">
        <div className="card">
          <h2>Bulk Watchlist Enrollment</h2>
          <p className="muted" style={{ marginBottom: '16px' }}>Bulk register multiple targets with unique files and metadata. (Requires Admin/Supervisor permissions).</p>

          <div className="form-group" style={{ marginBottom: "20px" }}>
            <label>Select Facial Scan Images (Select Multiple)</label>
            <input type="file" id="bulk-files-input" multiple accept="image/*" onChange={handleBulkFileChange} />
          </div>

          {bulkTargets.length > 0 && (
            <form onSubmit={handleBulkEnroll}>
              <div className="bulk-table-container">
                <table className="bulk-table">
                  <thead>
                    <tr>
                      <th>Filename</th>
                      <th>Target Name</th>
                      <th>Nationality</th>
                      <th>Date of Birth</th>
                      <th>Passport Number</th>
                      <th>Watchlist Tier</th>
                      <th>Enrollment Site</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bulkTargets.map((target, index) => (
                      <tr key={index} className="bulk-row">
                        <td className="bulk-file-badge">{target.filename}</td>
                        <td>
                          <input
                            type="text"
                            className="bulk-input"
                            value={target.name}
                            onChange={(e) => handleBulkTargetChange(index, "name", e.target.value)}
                            required
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            className="bulk-input"
                            value={target.nationality}
                            onChange={(e) => handleBulkTargetChange(index, "nationality", e.target.value)}
                            required
                          />
                        </td>
                        <td>
                          <input
                            type="date"
                            className="bulk-input"
                            value={target.dob}
                            onChange={(e) => handleBulkTargetChange(index, "dob", e.target.value)}
                            required
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            className="bulk-input"
                            value={target.passport_number}
                            onChange={(e) => handleBulkTargetChange(index, "passport_number", e.target.value)}
                          />
                        </td>
                        <td>
                          <select
                            className="bulk-input"
                            value={target.watchlist_tier}
                            onChange={(e) => handleBulkTargetChange(index, "watchlist_tier", parseInt(e.target.value))}
                          >
                            <option value={1}>Red Notice</option>
                            <option value={2}>Suspected HVT</option>
                            <option value={3}>POI</option>
                          </select>
                        </td>
                        <td>
                          <input
                            type="text"
                            className="bulk-input"
                            value={target.enrollment_site}
                            onChange={(e) => handleBulkTargetChange(index, "enrollment_site", e.target.value)}
                            required
                          />
                        </td>
                        <td>
                          {target.status === "idle" && <span className="status-indicator">Idle</span>}
                          {target.status === "pending" && <span className="status-indicator pending">Processing...</span>}
                          {target.status === "success" && <span className="status-indicator success">Success</span>}
                          {target.status === "error" && (
                            <span className="status-indicator error" title={target.errorDetail}>
                              Failed
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: "20px" }}>
                <button type="submit" className="run-evaluation" disabled={loadingBulk}>
                  {loadingBulk ? "Processing Bulk Biometrics..." : "Bulk Enroll Targets"}
                </button>
              </div>
            </form>
          )}

          {bulkMessage && (
            <div className={`message ${bulkError ? "error" : ""}`} style={{ marginTop: "16px" }}>
              {bulkMessage}
            </div>
          )}

          {bulkResult && (
            <div className={`bulk-result ${bulkResult.success_count === 0 ? "error" : ""}`}>
              <h4>Enrollment Summary:</h4>
              <p>Successfully processed <strong>{bulkResult.success_count}</strong> of <strong>{bulkResult.total_count}</strong> targets.</p>
              {bulkResult.results && bulkResult.results.length > 0 && (
                <ul style={{ marginTop: "8px" }}>
                  {bulkResult.results.map((r, i) => (
                    <li key={i} style={{ color: r.status === "success" ? "var(--green)" : "var(--red)" }}>
                      {r.filename}: {r.status === "success" ? `Enrolled as ${r.name}` : `Failed - ${r.detail}`}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Watchlist Management Section */}
      <section className="grid-full watchlist-management">
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border-glass)", paddingBottom: "16px", marginBottom: "16px" }}>
            <div>
              <h2>Watchlist Target Management</h2>
              <p className="muted">Detailed view of target identities currently enrolled in the biometric surveillance watchlist.</p>
            </div>
            <button className="role-btn" onClick={fetchWatchlist} disabled={loadingWatchlist} style={{ padding: "6px 12px" }}>
              {loadingWatchlist ? "Refreshing..." : "Refresh Watchlist"}
            </button>
          </div>

          {watchlistError && <div className="message error">{watchlistError}</div>}

          {watchlist.length === 0 ? (
            <div className="empty-state">No watchlist targets enrolled yet. Use Biometric Enrollment above.</div>
          ) : (
            <div className="watchlist-table-container">
              <table className="watchlist-table">
                <thead>
                  <tr>
                    <th>Target Name</th>
                    <th>Nationality</th>
                    <th>Passport Code</th>
                    <th>Date of Birth</th>
                    <th>Threat level</th>
                    <th>Enrollment Station</th>
                    <th>Registered Scans</th>
                    <th>Enrollment Time</th>
                  </tr>
                </thead>
                <tbody>
                  {watchlist.map((item) => (
                    <tr key={item.id}>
                      <td style={{ fontWeight: "700" }}>{item.name}</td>
                      <td>{item.nationality}</td>
                      <td>{item.passport_number}</td>
                      <td>{item.dob}</td>
                      <td>{getWatchlistTierBadge(item.watchlist_tier)}</td>
                      <td>{item.enrollment_site}</td>
                      <td style={{ fontWeight: "700", color: "var(--cyan)", textAlign: "center" }}>{item.photo_count || 1}</td>
                      <td>{item.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {/* Evaluation Dashboard Section */}
      <section className="grid-full evaluation-section">
        <div className="card">
          <div className="evaluation-header">
            <div>
              <h2>Evaluation Dashboard</h2>
              <p className="muted">Biometric model accuracy, timing characteristics, and confusion matrix classification metrics.</p>
            </div>
            <button
              className="run-evaluation-btn"
              onClick={handleRunEvaluation}
              disabled={loadingEvaluation}
            >
              {loadingEvaluation ? "Running Metrics..." : "Run Evaluation"}
            </button>
          </div>

          {evaluationError && (
            <div className="message error" style={{ marginTop: "16px" }}>
              <strong>Error:</strong> {evaluationError}
            </div>
          )}

          {!evaluationData ? (
            <div className="empty-evaluation" style={{ marginTop: "16px" }}>
              <p>No evaluation results found. Run evaluation first or add rmfrd_faiss_results.csv.</p>
            </div>
          ) : (
            <div style={{ marginTop: "24px" }}>
              {/* Metrics Grid */}
              <div className="evaluation-grid" style={{ marginBottom: "24px" }}>
                <div className="evaluation-card">
                  <div className="metric-label">Total Test Images</div>
                  <div className="metric-value">{evaluationData.total_tests || 0}</div>
                </div>
                <div className="evaluation-card">
                  <div className="metric-label">Accuracy</div>
                  <div className="metric-value">{formatScore(evaluationData.accuracy)}</div>
                </div>
                <div className="evaluation-card">
                  <div className="metric-label">Precision</div>
                  <div className="metric-value">{formatScore(evaluationData.precision)}</div>
                </div>
                <div className="evaluation-card">
                  <div className="metric-label">Recall</div>
                  <div className="metric-value">{formatScore(evaluationData.recall)}</div>
                </div>
                <div className="evaluation-card">
                  <div className="metric-label">F1-Score</div>
                  <div className="metric-value">{formatScore(evaluationData.f1_score)}</div>
                </div>
                <div className="evaluation-card">
                  <div className="metric-label">Top-1 Accuracy</div>
                  <div className="metric-value">{formatScore(evaluationData.top1_accuracy)}</div>
                </div>
                <div className="evaluation-card">
                  <div className="metric-label">Top-3 Accuracy</div>
                  <div className="metric-value">{formatScore(evaluationData.top3_accuracy)}</div>
                </div>
                <div className="evaluation-card">
                  <div className="metric-label">Avg Search Time</div>
                  <div className="metric-value">
                    {evaluationData.average_search_time !== null && evaluationData.average_search_time !== undefined
                      ? `${evaluationData.average_search_time.toFixed(3)}s`
                      : "0.000s"}
                  </div>
                </div>
              </div>

              {/* Confusion Matrix and Explanations */}
              <div className="confusion-matrix-container">
                <div>
                  <h3 style={{ marginBottom: "16px", fontSize: "16px", fontWeight: "700" }}>Confusion Matrix Values</h3>
                  <div className="confusion-matrix">
                    <div className="matrix-cell tp">
                      <div className="cell-value">{evaluationData.tp || 0}</div>
                      <div className="cell-label">True Positive (TP)</div>
                      <div className="cell-desc">Correct Watchlist Match</div>
                    </div>
                    <div className="matrix-cell fp">
                      <div className="cell-value">{evaluationData.fp || 0}</div>
                      <div className="cell-label">False Positive (FP)</div>
                      <div className="cell-desc">Incorrect Match</div>
                    </div>
                    <div className="matrix-cell fn">
                      <div className="cell-value">{evaluationData.fn || 0}</div>
                      <div className="cell-label">False Negative (FN)</div>
                      <div className="cell-desc">Missed Watchlist Identity</div>
                    </div>
                    <div className="matrix-cell tn">
                      <div className="cell-value">{evaluationData.tn || 0}</div>
                      <div className="cell-label">True Negative (TN)</div>
                      <div className="cell-desc">Correctly Rejected Unknown</div>
                    </div>
                  </div>
                </div>

                <div className="explanation-card">
                  <h3 style={{ marginBottom: "16px", fontSize: "16px", fontWeight: "700" }}>Metric Definitions</h3>
                  <table className="explanation-table">
                    <thead>
                      <tr>
                        <th>Metric</th>
                        <th>Definition / Meaning</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td style={{ color: "var(--green)" }}>TP</td>
                        <td>Correctly matched enrolled person</td>
                      </tr>
                      <tr>
                        <td style={{ color: "var(--red)" }}>FP</td>
                        <td>Incorrectly matched unknown/wrong person</td>
                      </tr>
                      <tr>
                        <td style={{ color: "var(--orange)" }}>FN</td>
                        <td>Failed to detect enrolled person</td>
                      </tr>
                      <tr>
                        <td style={{ color: "var(--blue)" }}>TN</td>
                        <td>Correctly rejected unknown person</td>
                      </tr>
                    </tbody>
                  </table>

                  <div style={{ marginTop: "20px", fontSize: "12px", color: "var(--text-muted)", borderTop: "1px solid var(--border-glass)", paddingTop: "12px" }}>
                    <strong>Last Updated:</strong> {evaluationData.last_updated || "Never"}
                    <br />
                    <strong>Dataset:</strong> {evaluationData.dataset_name || "N/A"}
                    <br />
                    <strong>Search Engine:</strong> {evaluationData.search_method || "N/A"}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Sentinel Eye Investigation Assistant RAG Section */}
      <section className="grid-full rag-section">
        <div className="card">
          <div className="rag-header">
            <h2>Sentinel Eye Investigation Assistant</h2>
            <p className="muted">Retrieve system documentation, check search logs, target alerts, and explain evaluation metrics.</p>
          </div>

          <div className="quick-question-buttons">
            <button
              className="quick-q-btn"
              onClick={(e) => handleAskRag(e, "What is Sentinel Eye?")}
              disabled={loadingRag}
            >
              What is Sentinel Eye?
            </button>
            <button
              className="quick-q-btn"
              onClick={(e) => handleAskRag(e, "Summarize latest alerts")}
              disabled={loadingRag}
            >
              Summarize latest alerts
            </button>
            <button
              className="quick-q-btn"
              onClick={(e) => handleAskRag(e, "Explain evaluation results")}
              disabled={loadingRag}
            >
              Explain evaluation results
            </button>
            <button
              className="quick-q-btn"
              onClick={(e) => handleAskRag(e, "What is FAISS?")}
              disabled={loadingRag}
            >
              What is FAISS?
            </button>
            <button
              className="quick-q-btn"
              onClick={(e) => handleAskRag(e, "What are TP, FP, FN, TN?")}
              disabled={loadingRag}
            >
              What are TP, FP, FN, TN?
            </button>
          </div>

          <form onSubmit={handleAskRag}>
            <textarea
              className="rag-textarea"
              placeholder="Ask about alerts, evaluation, audit logs, or system architecture..."
              value={ragQuestion}
              onChange={(e) => setRagQuestion(e.target.value)}
              disabled={loadingRag}
            />
            <div className="rag-actions">
              {loadingRag && <span className="muted">Analyzing context and generating answer...</span>}
              <button
                type="submit"
                className="run-evaluation"
                disabled={loadingRag || !ragQuestion.trim()}
              >
                {loadingRag ? "Querying..." : "Ask Assistant"}
              </button>
            </div>
          </form>

          {ragError && (
            <div className="message error" style={{ marginTop: "16px" }}>
              <strong>Error:</strong> {ragError}
            </div>
          )}

          {ragAnswer && (
            <div className="rag-answer">
              <div style={{ whiteSpace: "pre-line" }}>
                {ragAnswer}
              </div>

              {ragSources && ragSources.length > 0 && (
                <div className="rag-sources">
                  <span>Sources Used:</span>
                  {ragSources.map((source, index) => (
                    <span key={index} className="source-badge">
                      {source}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Alerts Logs History */}
      <section className="grid-full">
        <div className="card alerts-section">
          <h2>Active Watchlist Alerts</h2>
          {alerts.length === 0 ? (
            <p className="muted" style={{ padding: "20px" }}>
              No alerts generated.
            </p>
          ) : (
            <div className="alerts-table">
              <div className="table-header">
                <span>Subject Name</span>
                <span>Match Score</span>
                <span>Threat Level</span>
                <span>Status</span>
                <span>Capture Origin</span>
                <span>Timestamp</span>
              </div>

              {alerts.map((alert) => (
                <div className="table-row" key={alert.id}>
                  <span style={{ fontWeight: "700" }}>{alert.name}</span>
                  <span style={{ color: "var(--cyan)", fontWeight: "700" }}>{formatScore(alert.score)}</span>
                  <span>
                    {alert.alert_level === "critical" ? (
                      <span className="badge badge-red">Critical</span>
                    ) : (
                      <span className="badge badge-orange">Warning</span>
                    )}
                  </span>
                  <span>
                    <span className="badge badge-blue">{alert.status}</span>
                  </span>
                  <span>{alert.camera}</span>
                  <span>{alert.created_at}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Searches Logs History */}
      <section className="grid-full">
        <div className="card alerts-section">
          <h2>Surveillance Audit Logs</h2>
          {searches.length === 0 ? (
            <p className="muted" style={{ padding: "20px" }}>
              No audit trails recorded.
            </p>
          ) : (
            <div className="alerts-table">
              <div className="table-header">
                <span>Evaluated Subject</span>
                <span>Best Match Score</span>
                <span>Retrieval Status</span>
                <span>Review Level</span>
                <span>Camera Origin</span>
                <span>Timestamp</span>
              </div>

              {searches.map((search) => (
                <div className="searches-table-row" key={search.id}>
                  <span style={{ fontWeight: "700" }}>{search.best_match}</span>
                  <span style={{ color: "var(--cyan)", fontWeight: "700" }}>{formatScore(search.score)}</span>
                  <span>
                    {search.status === "match" ? (
                      <span className="badge badge-green">Match</span>
                    ) : (
                      <span className="badge badge-blue">Unknown</span>
                    )}
                  </span>
                  <span>{search.status === "match" ? "High Alert" : "Logged Only"}</span>
                  <span>{search.camera}</span>
                  <span>{search.created_at}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default App;