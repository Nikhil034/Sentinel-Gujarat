import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export default function CameraMap({ cameras, selectedId, onSelect, trail = [], gapIds = {} }) {
  const center = [22.7, 71.6];
  const line = trail
    .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng))
    .map((p) => [p.lat, p.lng]);
  const unlocated = new Set(gapIds.unlocated || []);
  const silent = new Set(gapIds.silent || []);

  function pinColor(cam) {
    if (unlocated.has(cam.id)) return "#f0c674";
    if (silent.has(cam.id)) return "#9ecbff";
    return cam.status === "online" ? "#5ee0a0" : "#f07178";
  }

  return (
    <MapContainer className="map" center={center} zoom={7} scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {line.length >= 2 && (
        <Polyline positions={line} pathOptions={{ color: "#ff4d4f", weight: 4 }} />
      )}
      {cameras.map((cam) => (
        <CircleMarker
          key={cam.id}
          center={[cam.lat, cam.lng]}
          radius={selectedId === cam.id ? 12 : 8}
          pathOptions={{
            color: pinColor(cam),
            fillColor: pinColor(cam),
            fillOpacity: 0.9,
          }}
          eventHandlers={{ click: () => onSelect(cam.id) }}
        >
          <Popup>
            <strong>{cam.name}</strong>
            <br />
            {cam.city} · {cam.location}
            <br />
            {cam.department || "—"} · {cam.status}
            {unlocated.has(cam.id) ? " · unlocated" : ""}
            {silent.has(cam.id) ? " · no events yet" : ""}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
