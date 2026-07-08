import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [name, setName] = useState("");
  const [registerFile, setRegisterFile] = useState(null);
  const [recognizeFile, setRecognizeFile] = useState(null);
  const [robustMode, setRobustMode] = useState(false);
  const [camera, setCamera] = useState("Camera 1 - Main Gate");

  const [registerMessage, setRegisterMessage] = useState("");
  const [result, setResult] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [searches, setSearches] = useState([]);

  const [stats, setStats] = useState({
    total_users: 0,
    total_alerts: 0,
    total_searches: 0,
  });

  const [loadingRegister, setLoadingRegister] = useState(false);
  const [loadingRecognize, setLoadingRecognize] = useState(false);

  const formatScore = (score) => {
    if (score === undefined || score === null) return "0%";
    return `${(score * 100).toFixed(2)}%`;
  };

  const getResultTitle = () => {
    if (!result) return "";

    if (!result.match) return "No Confirmed Match";

    if (result.alert_level === "strong") return "Strong Match";
    if (result.alert_level === "possible") return "Possible Match";
    if (result.alert_level === "low possible") return "Low Possible Match";

    return "Match Found";
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
  }, []);

  const handleRegister = async (e) => {
    e.preventDefault();

    if (!name || !registerFile) {
      setRegisterMessage("Please enter name and choose an image.");
      return;
    }

    setLoadingRegister(true);
    setRegisterMessage("");

    try {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("file", registerFile);

      const res = await fetch(`${API_URL}/register`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Registration failed.");
      }

      setRegisterMessage(data.message);
      setName("");
      setRegisterFile(null);

      await loadDashboard();
    } catch (error) {
      setRegisterMessage(error.message);
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
      formData.append("mode", robustMode ? "robust" : "normal");
      formData.append("camera", camera);

      const res = await fetch(`${API_URL}/recognize`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Recognition failed.");
      }

      setResult(data);
      await loadDashboard();
    } catch (error) {
      setResult({
        match: false,
        name: "Error",
        score: 0,
        confidence: "none",
        error: error.message,
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
      </header>

      <section className="dashboard">
        <div className="card stat-card">
          <h3>Total Watchlist Identities</h3>
          <p>{stats.total_users}</p>
        </div>

        <div className="card stat-card">
          <h3>Total Searches</h3>
          <p>{stats.total_searches}</p>
        </div>

        <div className="card stat-card">
          <h3>Total Alerts</h3>
          <p>{stats.total_alerts}</p>
        </div>

        <div className="card stat-card">
          <h3>Recognition Mode</h3>
          <p>{robustMode ? "Robust" : "Normal"}</p>
        </div>
      </section>

      <main className="grid">
        <section className="card">
          <h2>Add Watchlist Identity</h2>
          <p className="muted">Register a person using a clear full-face image.</p>

          <form onSubmit={handleRegister}>
            <label>Name</label>
            <input
              type="text"
              placeholder="Enter person name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />

            <label>Face Image</label>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setRegisterFile(e.target.files[0])}
            />

            <button type="submit" disabled={loadingRegister}>
              {loadingRegister ? "Registering..." : "Register Identity"}
            </button>
          </form>

          {registerMessage && <div className="message">{registerMessage}</div>}
        </section>

        <section className="card">
          <h2>Face Search / Surveillance Check</h2>
          <p className="muted">Upload a face image to search for the closest match.</p>

          <form onSubmit={handleRecognize}>
            <label>Search Image</label>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setRecognizeFile(e.target.files[0])}
            />

            <label>Camera / Location</label>
            <select value={camera} onChange={(e) => setCamera(e.target.value)}>
              <option>Camera 1 - Main Gate</option>
              <option>Camera 2 - Lobby</option>
              <option>Camera 3 - Parking Area</option>
              <option>Camera 4 - Reception</option>
            </select>

            <div className="checkbox-row">
              <input
                type="checkbox"
                checked={robustMode}
                onChange={(e) => setRobustMode(e.target.checked)}
              />
              <span>Use masked / unclear face mode</span>
            </div>

            <button type="submit" disabled={loadingRecognize}>
              {loadingRecognize ? "Processing..." : "Search Face"}
            </button>
          </form>

          {result && (
            <div className={result.match ? "result success" : "result fail"}>
              <h3>{getResultTitle()}</h3>

              <p><strong>Name:</strong> {result.name}</p>
              <p><strong>Score:</strong> {formatScore(result.score)}</p>
              <p><strong>Confidence:</strong> {result.confidence}</p>
              <p><strong>Alert Level:</strong> {result.alert_level || "unknown"}</p>
              <p><strong>Mode:</strong> {result.mode || "normal"}</p>
              <p><strong>Camera:</strong> {result.camera || camera}</p>

              {result.error && <p><strong>Error:</strong> {result.error}</p>}

              {result.alert?.generated && (
                <div className="alert-box">
                  🚨 {result.alert.message}
                </div>
              )}

              {result.top_matches && result.top_matches.length > 0 && (
                <div className="top-matches">
                  <h4>Top Matches</h4>

                  {result.top_matches.map((item, index) => (
                    <div key={index} className="match-row">
                      <span>{index + 1}. {item.name}</span>
                      <span>{formatScore(item.score)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </main>

      <section className="card alerts-section">
        <h2>Alert History</h2>

        {alerts.length === 0 ? (
          <p className="muted">No alerts yet.</p>
        ) : (
          <div className="alerts-table">
            <div className="table-header">
              <span>Name</span>
              <span>Score</span>
              <span>Level</span>
              <span>Mode</span>
              <span>Camera</span>
              <span>Time</span>
            </div>

            {alerts.map((alert) => (
              <div className="table-row" key={alert.id}>
                <span>{alert.name}</span>
                <span>{formatScore(alert.score)}</span>
                <span>{alert.alert_level}</span>
                <span>{alert.mode}</span>
                <span>{alert.camera}</span>
                <span>{alert.created_at}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card alerts-section">
        <h2>Search History</h2>

        {searches.length === 0 ? (
          <p className="muted">No searches yet.</p>
        ) : (
          <div className="alerts-table">
            <div className="table-header">
              <span>Best Match</span>
              <span>Score</span>
              <span>Status</span>
              <span>Mode</span>
              <span>Camera</span>
              <span>Time</span>
            </div>

            {searches.map((search) => (
              <div className="table-row" key={search.id}>
                <span>{search.best_match}</span>
                <span>{formatScore(search.score)}</span>
                <span>{search.status}</span>
                <span>{search.mode}</span>
                <span>{search.camera}</span>
                <span>{search.created_at}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default App;