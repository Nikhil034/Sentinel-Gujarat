import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export default function CameraMap({ cameras, selectedId, onSelect, trail = [] }) {
  const center = [22.7, 71.6];
  const line = trail
    .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng))
    .map((p) => [p.lat, p.lng]);

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
            color: cam.status === "online" ? "#5ee0a0" : "#f07178",
            fillColor: cam.status === "online" ? "#5ee0a0" : "#f07178",
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
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
