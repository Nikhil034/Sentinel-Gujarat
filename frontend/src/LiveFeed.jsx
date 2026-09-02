import { useEffect, useRef } from "react";
import Hls from "hls.js";

export default function LiveFeed({ cam, compact = false }) {
  const videoRef = useRef(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || cam?.source_type === "file" || compact) return undefined;
    const src = `/live/${encodeURIComponent(cam.id)}/index.m3u8`;
    let hls;
    const jumpLive = () => {
      if (video.duration && Number.isFinite(video.duration) && video.duration > 1) {
        try {
          video.currentTime = (Date.now() / 1000) % video.duration;
        } catch {
          /* ignore */
        }
      }
    };
    video.addEventListener("loadedmetadata", jumpLive);
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = src;
    } else if (Hls.isSupported()) {
      hls = new Hls({ enableWorker: true, maxBufferLength: 12, startPosition: -1 });
      hls.loadSource(src);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, jumpLive);
    }
    return () => {
      video.removeEventListener("loadedmetadata", jumpLive);
      if (hls) hls.destroy();
      video.removeAttribute("src");
      video.load();
    };
  }, [cam?.id, cam?.source_type, compact]);

  if (cam?.source_type === "file" && cam.video_url) {
    return <video className="player" src={cam.video_url} controls playsInline />;
  }
  if (compact) {
    return (
      <p className="sub">
        {cam.name} · click the list to play HLS
      </p>
    );
  }
  return (
    <>
      <video ref={videoRef} className="player live-embed" controls muted autoPlay playsInline />
      <p className="sub">
        In-app HLS via our session cookie. Official wall:{" "}
        <a href="https://cctv.corp8.cloud/" target="_blank" rel="noreferrer">
          cctv.corp8.cloud
        </a>
      </p>
    </>
  );
}
