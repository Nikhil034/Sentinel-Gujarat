"""Proxy official HLS (cookie + AES key) so the browser can play it."""

from __future__ import annotations

import re
import urllib.error
import urllib.request

from sentinel import get_opener, normalize_cam_id, official_hls, portal_origin
from store import get_camera

_SAFE = re.compile(r"^[A-Za-z0-9._-]+$")


def _fetch(url: str) -> tuple[bytes, str]:
    opener = get_opener()
    origin = portal_origin()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SentinelCommand/0.8",
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Referer": f"{origin}/",
            "Origin": origin,
        },
    )
    with opener.open(req, timeout=25) as resp:
        ctype = resp.headers.get("Content-Type") or "application/octet-stream"
        return resp.read(), ctype


def _rewrite_playlist(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("#EXT-X-KEY"):
            line = re.sub(r'URI="[^"]+"', 'URI="enc.key"', line)
            line = re.sub(r"URI='[^']+'", "URI='enc.key'", line)
        elif line.strip() and not line.startswith("#"):
            name = line.strip().rsplit("/", 1)[-1]
            line = name
        lines.append(line)
    return "\n".join(lines) + "\n"


def live_asset(camera_id: str, name: str) -> tuple[bytes, str]:
    if not _SAFE.match(name):
        raise ValueError("Invalid asset name")
    cam = get_camera(camera_id)
    if not cam or cam.get("source_type") == "file":
        raise FileNotFoundError("Not a live Sentinel camera")
    remote = normalize_cam_id(cam.get("remote_id") or camera_id)
    origin = portal_origin()
    if name == "index.m3u8":
        body, _ = _fetch(official_hls(remote))
        if body.lstrip()[:15].lower().startswith(b"<!doctype") or b"Access Password" in body[:400]:
            raise PermissionError("Grid login expired — sign in again.")
        return _rewrite_playlist(body.decode("utf-8", "replace")).encode(), "application/vnd.apple.mpegurl"
    if name == "enc.key":
        body, _ = _fetch(f"{origin}/enc.key")
        return body, "application/octet-stream"
    body, _ = _fetch(f"{origin}/{remote}/{name}")
    if name.endswith(".ts"):
        return body, "video/MP2T"
    return body, "application/octet-stream"
