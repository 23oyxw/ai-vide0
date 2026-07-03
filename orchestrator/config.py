from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    video_factory_path: Path = Path(r"C:\Users\oyxw\Projects\video-factory")
    ai_koubo_path: Path = Path(r"C:\Users\oyxw\Projects\ai-koubo-platform")
    c4d_root: Path = Path(r"C:\BKC4D")
    ffmpeg_path: Path = Path(r"C:\Users\oyxw\bin\ffmpeg\ffmpeg.exe")
    openclaw_bin: str = "openclaw"

    orchestrator_host: str = "127.0.0.1"
    orchestrator_port: int = 8765

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "orchestrator"
    mysql_password: str = "orchestrator"
    mysql_database: str = "ai_video"
    redis_url: str = "redis://127.0.0.1:6379/0"
    qdrant_url: str = "http://127.0.0.1:6333"

    @property
    def c4d_commandline(self) -> Path:
        return self.c4d_root / "Commandline.exe"


settings = Settings()
