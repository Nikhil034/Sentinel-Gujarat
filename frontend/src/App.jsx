import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import CameraMap from "./CameraMap.jsx";
import LiveFeed from "./LiveFeed.jsx";

const API = import.meta.env.VITE_API_URL || "";

function eventWhen(ev) {
  if (ev?.captured_at && ev.clock !== "clip") {
    try {
      return (
        new Date(ev.captured_at).toLocaleString("en-IN", {
          timeZone: "Asia/Kolkata",
          day: "2-digit",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        }) + " IST"
      );
    } catch {
      /* use clip time */
    }
  }
  const s = Number(ev?.t_sec) || 0;
  const m = Math.floor(s / 60);
  const r = Math.floor(s % 60);
  return `clip ${m}:${String(r).padStart(2, "0")}`;
}

function beep() {
  try {
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "square";
    osc.frequency.value = 880;
    gain.gain.value = 0.05;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.18);
  } catch {
    /* ignore */
  }
}

export default function App() {
  const [cameras, setCameras] = useState([]);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState("");
  const [events, setEvents] = useState([]);
  const [busy, setBusy] = useState("");
  const [note, setNote] = useState("");
  const [watchlist, setWatchlist] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [plateIn, setPlateIn] = useState("GJ01AB1234");
  const [reasonIn, setReasonIn] = useState("stolen");
  const [huntPlate, setHuntPlate] = useState("GJ01AB1234");
  const [hunt, setHunt] = useState(null);
  const [pathStatus, setPathStatus] = useState(null);
  const [gap, setGap] = useState(null);
  const [gridPass, setGridPass] = useState("");
  const [showWall, setShowWall] = useState(false);
  const lastAlertCount = useRef(0);

  const refresh = useCallback(() => {
    fetch(`${API}/cameras`)
      .then((r) => r.json())
      .then((c) => {
        const list = c.cameras || [];
        setCameras(list);
        setError("");
        setSelectedId((prev) => prev || list[0]?.id || "");
      })
      .catch((e) => setError(e.message));
  }, []);

  const loadEvents = useCallback((id) => {
    if (!id) return;
    fetch(`${API}/events?camera_id=${encodeURIComponent(id)}`)
      .then((r) => r.json())
      .then((e) => setEvents(e.events || []))
      .catch(() => setEvents([]));
  }, []);

  const loadWatchlist = useCallback(() => {
    fetch(`${API}/watchlist`)
      .then((r) => r.json())
      .then((w) => setWatchlist(w.items || []))
      .catch(() => setWatchlist([]));
  }, []);

  const loadPath = useCallback(() => {
    fetch(`${API}/sentinel/status`)
      .then((r) => r.json())
      .then((s) => setPathStatus(s))
      .catch(() => setPathStatus(null));
    fetch(`${API}/cameras/gap`)
      .then((r) => r.json())
      .then((g) => setGap(g))
      .catch(() => setGap(null));
  }, []);

  const loadAlerts = useCallback(() => {
    fetch(`${API}/alerts`)
      .then((r) => r.json())
      .then((a) => setAlerts(a.alerts || []))
      .catch(() => setAlerts([]));
  }, []);

  useEffect(() => {
    refresh();
    loadWatchlist();
    loadAlerts();
    loadPath();
  }, [refresh, loadWatchlist, loadAlerts, loadPath]);

  useEffect(() => {
    loadEvents(selectedId);
  }, [selectedId, loadEvents]);

  useEffect(() => {
    if (alerts.length > lastAlertCount.current) beep();
    lastAlertCount.current = alerts.length;
  }, [alerts]);

  const wanted = useMemo(
    () => new Set(watchlist.map((w) => (w.plate_norm || w.plate || "").replace(/[^A-Z0-9]/gi, "").toUpperCase())),
    [watchlist]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return cameras;
    return cameras.filter((cam) =>
      [cam.name, cam.location, cam.city, cam.status, cam.source_type]
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }, [cameras, query]);

  const selected = cameras.find((c) => c.id === selectedId) || filtered[0];
  const latestAlert = alerts[alerts.length - 1];

  async function extract(id) {
    setBusy("extract-" + id);
    try {
      const res = await fetch(`${API}/cameras/${id}/extract`, { method: "POST" });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Extract failed");
      const via = body.method === "hls" ? "HLS (RTSP :8554 blocked here)" : body.method;
      setNote(`Captured ${body.extracted} frames via ${via}.`);
      setError("");
      refresh();
      loadPath();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  async function fetchGrid() {
    setBusy("ingest");
    setNote("Fetching official /api/ingest catalogue…");
    try {
      const res = await fetch(`${API}/cameras/sentinel/import`, { method: "POST" });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Ingest failed");
      setNote(`Imported ${body.imported} Sentinel cameras (${body.created} new).`);
      refresh();
      loadPath();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  async function analyze(id) {
    setBusy("analyze-" + id);
    setNote("Detecting… live RTSP uses TCP + PTS per integrator guide.");
    try {
      const res = await fetch(`${API}/cameras/${id}/analyze`, { method: "POST" });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Analyze failed");
      setNote(`${body.vehicles || 0} vehicles · ${body.plates || 0} plates`);
      refresh();
      loadEvents(id);
      loadAlerts();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  async function onCsv(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API}/cameras/import`, { method: "POST", body: form });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Import failed");
      refresh();
    } catch (err) {
      setError(err.message);
    }
    e.target.value = "";
  }

  async function addPlate(e) {
    e.preventDefault();
    try {
      const res = await fetch(`${API}/watchlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plate: plateIn, reason: reasonIn }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Watchlist failed");
      loadWatchlist();
      loadAlerts();
      setNote(`Watchlist: ${body.plate} (${body.reason})`);
    } catch (err) {
      setError(err.message);
    }
  }

  async function removePlate(plate) {
    await fetch(`${API}/watchlist/${encodeURIComponent(plate)}`, { method: "DELETE" });
    loadWatchlist();
    loadAlerts();
  }

  async function runHunt(e) {
    e.preventDefault();
    try {
      const res = await fetch(`${API}/hunt?plate=${encodeURIComponent(huntPlate)}`);
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Hunt failed");
      setHunt(body);
      if (body.cameras?.[0]?.id) setSelectedId(body.cameras[0].id);
    } catch (err) {
      setError(err.message);
    }
  }

  async function signInGrid(e) {
    e.preventDefault();
    setBusy("login");
    try {
      const res = await fetch(`${API}/sentinel/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: gridPass }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Grid login failed");
      setNote(body.detail || "Signed in to Sentinel grid.");
      setGridPass("");
      setError("");
      loadPath();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  const online = cameras.filter((c) => c.status === "online").length;

  return (
    <div className="layout">
      <header className="top">
        <div>
          <h1>Sentinel Command</h1>
          <p className="sub">Hybrid Model 1 + 2 — GIS registry, live watch, ANPR, watchlist, hunt.</p>
        </div>
        <p className="stats">
          {cameras.length} cameras · {online} online · {alerts.length} alerts
        </p>
      </header>

      {alerts.length > 0 && latestAlert && (
        <div className="banner">
          STOLEN PLATE {latestAlert.plate} · {latestAlert.reason} · {latestAlert.camera_name} ·{" "}
          {eventWhen(latestAlert)}
        </div>
      )}

      {pathStatus && (
        <p className={pathStatus.capture_path === "blocked" || pathStatus.capture_path === "auth" ? "warn" : "ok"}>
          Grid {pathStatus.auth?.logged_in ? "signed in" : "login needed"}
          {" · "}
          ingest {pathStatus.ingest?.ok ? "ok" : "fail"}
          {" · "}
          RTSP :8554 {pathStatus.rtsp_8554?.ok ? "open" : "blocked"}
          {" · "}
          HLS {pathStatus.hls?.ok ? "ok" : "blocked"}
          {" — "}
          {pathStatus.summary}
        </p>
      )}
      {gap && (
        <p className="gap-line">
          Coverage: {gap.official_grid} official · {gap.own_recorded} own-feed · cities{" "}
          {Object.entries(gap.by_city || {})
            .map(([city, n]) => `${city} (${n})`)
            .join(", ")}
          {gap.unlocated?.length ? ` · ${gap.unlocated.length} unlocated pins` : ""}
          {" · "}
          <a href={`${API}/cameras.csv`}>Export registry CSV</a>
        </p>
      )}
      {error && <p className="warn">{error}</p>}
      {note && <p className="ok">{note}</p>}

      <CameraMap
        cameras={filtered}
        selectedId={selected?.id}
        onSelect={setSelectedId}
        trail={hunt?.cameras || []}
      />

      <div className="ops">
        <form className="card ops-card" onSubmit={addPlate}>
          <strong>Watchlist</strong>
          <input value={plateIn} onChange={(e) => setPlateIn(e.target.value)} placeholder="GJ01AB1234" />
          <input value={reasonIn} onChange={(e) => setReasonIn(e.target.value)} placeholder="stolen" />
          <button type="submit">Add plate</button>
          {watchlist.map((w) => (
            <p key={w.plate}>
              <code>{w.plate}</code> · {w.reason}{" "}
              <button type="button" className="ghost" onClick={() => removePlate(w.plate)}>
                Remove
              </button>
            </p>
          ))}
        </form>

        <form className="card ops-card" onSubmit={runHunt}>
          <strong>Hunt</strong>
          <input value={huntPlate} onChange={(e) => setHuntPlate(e.target.value)} placeholder="Type plate" />
          <button type="submit">Find trail</button>
          {hunt && (
            <p className="ok">
              {hunt.plate}: {hunt.hit_count} hits · {hunt.cameras.length} cameras
              {hunt.hit_count > 0 && (
                <>
                  {" "}
                  <a href={`${API}/hunt.csv?plate=${encodeURIComponent(hunt.plate)}`}>Export CSV</a>
                </>
              )}
            </p>
          )}
          {hunt?.hits?.slice(0, 12).map((hit) => (
            <p key={hit.id}>
              {hit.camera_name} · {eventWhen(hit)} · {hit.plate}
            </p>
          ))}
        </form>

        <form className="card ops-card" onSubmit={signInGrid}>
          <strong>Sentinel grid login</strong>
          <p className="sub">Password from cctv.corp8.cloud — needed for live ingest / HLS ANPR.</p>
          <input
            type="password"
            value={gridPass}
            onChange={(e) => setGridPass(e.target.value)}
            placeholder="XXXX-XXXX-XXXX"
            autoComplete="off"
          />
          <button type="submit" disabled={!!busy || !gridPass}>
            {busy === "login" ? "Signing in…" : "Sign in to grid"}
          </button>
          <p>
            <a href="https://cctv.corp8.cloud/auth/register" target="_blank" rel="noreferrer">
              Register for a password
            </a>
            {" · "}
            <a href="https://cctv.corp8.cloud/resource" target="_blank" rel="noreferrer">
              Integrator guide
            </a>
          </p>
        </form>
      </div>

      <div className="toolbar">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by city, name, Paldi, Junagadh…"
        />
        <button className="csv" type="button" disabled={!!busy} onClick={fetchGrid}>
          {busy === "ingest" ? "Fetching grid…" : "Fetch Sentinel grid"}
        </button>
        <label className="csv">
          Import CSV
          <input type="file" accept=".csv,text/csv" onChange={onCsv} hidden />
        </label>
        <button className="csv" type="button" onClick={() => setShowWall((v) => !v)}>
          {showWall ? "Hide live wall" : "Show 4-up wall"}
        </button>
      </div>

      {showWall && (
        <div className="wall">
          {filtered.slice(0, 4).map((cam) => (
            <div className="tile" key={`wall-${cam.id}`}>
              <strong>
                {cam.name} · {cam.city || cam.source_type}
              </strong>
              <LiveFeed cam={cam} compact />
            </div>
          ))}
        </div>
      )}

      <div className="split">
        <div className="list">
          {filtered.map((cam) => (
            <button
              key={cam.id}
              className={`row ${selected?.id === cam.id ? "active" : ""}`}
              onClick={() => setSelectedId(cam.id)}
            >
              <span className={`dot ${cam.status}`} />
              <span>
                <strong>{cam.name}</strong>
                <small>
                  {cam.city || "—"} · {cam.department || cam.location}
                </small>
              </span>
            </button>
          ))}
        </div>

        {selected && (
          <div className="card detail">
            <strong>{selected.name}</strong>
            <p>
              {selected.city} · {selected.department || "—"} · {selected.location}
            </p>
            <p className={selected.status === "online" ? "ok" : "warn"}>
              {selected.status} · {selected.source_type === "file" ? "recorded clip" : "live camera"}
            </p>
            <p>
              <code>{selected.source_url}</code>
            </p>

            <LiveFeed cam={selected} />
            <p className="sub">
              Fetch grid only registers the camera on the map. Events appear after you click
              Detect on that camera. Video plays here for official HLS; own-feed clips play from disk.
            </p>

            <p>
              <button disabled={!!busy} onClick={() => extract(selected.id)}>
                {busy.startsWith("extract")
                  ? "Capturing…"
                  : selected.source_type === "file"
                    ? "Extract frames"
                    : "Capture frames (RTSP TCP, then HLS)"}
              </button>{" "}
              <button disabled={!!busy} onClick={() => analyze(selected.id)}>
                {busy.startsWith("analyze") ? "Detecting…" : "Detect vehicles + plates"}
              </button>{" "}
              <span className={selected.snapshot_count ? "ok" : "warn"}>
                {selected.snapshot_count} stills · {selected.event_count || 0} events
              </span>
            </p>
            <p className="sub">
              {selected.source_type === "file"
                ? "Times below are position in the clip. Old stills are capped so the folder does not grow."
                : "Times below are the live clock (IST), not 0s/1s. Capture is a short sample — not 24-hour storage. Raw frames are deleted after detect."}
            </p>

            {(selected.latest_annotated || selected.latest_snapshot) && (
              <img
                className="snap"
                src={selected.latest_annotated || selected.latest_snapshot}
                alt={`Latest frame from ${selected.name}`}
              />
            )}

            {events.length > 0 && (
              <div className="events">
                <strong>Events</strong>
                {events.map((ev) => {
                  const plate = (ev.plate || "").replace(/[^A-Z0-9]/gi, "").toUpperCase();
                  const hot = plate && wanted.has(plate);
                  return (
                    <p key={ev.id} className={hot ? "hot" : ""}>
                      {eventWhen(ev)} · {ev.label}
                      {ev.plate ? ` · ${ev.plate}` : " · plate unread"}
                      {hot ? " · WATCHLIST" : ""}
                    </p>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
