from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    videos_dir: Path = Path("data/videos")
    snapshots_dir: Path = Path("data/snapshots")
    sample_camera_name: str = "Cam-YT-01"
    sample_video: Path = Path("data/videos/sample.mp4")
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # Official sandbox: password gate on cctv.corp8.cloud, RTSP on a public IP.
    sentinel_ingest_url: str = "https://cctv.corp8.cloud/cameras.json"
    sentinel_hls_host: str = "https://cctv.corp8.cloud"
    sentinel_portal: str = "https://cctv.corp8.cloud"
    sentinel_rtsp_host: str = "103.250.160.189"
    sentinel_password: str = ""
    # Disk: this is a short sample, not a 24h DVR.
    snapshot_keep_annotated: int = 8
    snapshot_keep_file_frames: int = 24
    delete_raw_after_analyze: bool = True

    @field_validator("videos_dir", "snapshots_dir", "sample_video", mode="before")
    @classmethod
    def resolve_under_root(cls, value):
        path = Path(value)
        if not path.is_absolute():
            path = ROOT / path
        return path


settings = Settings()
settings.videos_dir.mkdir(parents=True, exist_ok=True)
settings.snapshots_dir.mkdir(parents=True, exist_ok=True)
