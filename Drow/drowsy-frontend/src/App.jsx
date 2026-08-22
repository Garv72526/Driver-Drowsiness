import { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./App.css";

const BASE = "http://localhost:5004";

export default function App() {
  const videoRef   = useRef(null);
  const canvasRef  = useRef(null);
  const intervalRef= useRef(null);

  const [running, setRunning] = useState(false);
  const [data,    setData]    = useState(null);
  const [error,   setError]   = useState("");

  // Start webcam
  async function start() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      setRunning(true);
      setError("");
    } catch {
      setError("Could not access webcam.");
    }
  }

  // Stop webcam
  function stop() {
    videoRef.current?.srcObject?.getTracks().forEach(t => t.stop());
    clearInterval(intervalRef.current);
    setRunning(false);
    setData(null);
  }

  // Send frames to Flask every 100ms
  useEffect(() => {
    if (!running) return;

    intervalRef.current = setInterval(async () => {
      const video  = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas) return;

      // Draw current frame to canvas
      const ctx = canvas.getContext("2d");
      canvas.width  = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);

      // Convert to base64 and send
      const frame = canvas.toDataURL("image/jpeg", 0.7);
      try {
        const res = await axios.post(`${BASE}/process`, { frame });
        setData(res.data);
      } catch { /* skip failed frames */ }
    }, 100);

    return () => clearInterval(intervalRef.current);
  }, [running]);

  // Risk color
  const colors = { Safe: "#16a34a", Warning: "#d97706", Danger: "#dc2626" };
  const color  = colors[data?.risk] || "#888";

  return (
    <div className="app">
      <h1>🚗 Driver Safety Monitor</h1>

      <div className="layout">

        {/* Webcam */}
        <div className="video-wrap">
          <video ref={videoRef} className="video" muted playsInline />
          <canvas ref={canvasRef} hidden />
          {data?.alert && <div className="alert">{data.alert}</div>}
          <div className="btns">
            {!running
              ? <button onClick={start}>▶ Start</button>
              : <button onClick={stop} className="red">■ Stop</button>
            }
            <button onClick={() => axios.post(`${BASE}/reset`)}>↺ Reset</button>
          </div>
          {error && <p className="error">{error}</p>}
        </div>

        {/* Dashboard */}
        {data && (
          <div className="dashboard">

            {/* Risk */}
            <div className="card" style={{ borderColor: color }}>
              <p className="label">Risk Level</p>
              <p className="big" style={{ color }}>{data.risk}</p>
            </div>

            {/* Score */}
            <div className="card">
              <p className="label">Safety Score</p>
              <p className="big">{data.safety_score}<span>/100</span></p>
              <div className="bar">
                <div className="fill" style={{
                  width: `${data.safety_score}%`,
                  background: color
                }}/>
              </div>
            </div>

            {/* Metrics */}
            <div className="card">
              <p className="label">Live Metrics</p>
              <div className="row">
                <span>EAR</span>
                <span style={{ color: data.ear < 0.25 ? "#dc2626" : "#16a34a" }}>
                  {data.ear}
                </span>
              </div>
              <div className="row">
                <span>MAR</span>
                <span style={{ color: data.mar > 0.4 ? "#dc2626" : "#16a34a" }}>
                  {data.mar}
                </span>
              </div>
              <div className="row">
                <span>Head Angle</span>
                <span style={{ color: data.angle > 30 ? "#dc2626" : "#16a34a" }}>
                  {data.angle}°
                </span>
              </div>
            </div>

            {/* Status */}
            <div className="card">
              <p className="label">Detections</p>
              {[
                { key: "drowsy",     label: "Drowsy" },
                { key: "yawning",    label: "Yawning" },
                { key: "distracted", label: "Distracted" },
              ].map(({ key, label }) => (
                <div key={key} className="row">
                  <span>{label}</span>
                  <span className={data[key] ? "bad" : "good"}>
                    {data[key] ? "⚠ YES" : "✓ OK"}
                  </span>
                </div>
              ))}
            </div>

          </div>
        )}
      </div>
    </div>
  );
}