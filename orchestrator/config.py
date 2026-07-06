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
    ai_koubo_url: str = "http://127.0.0.1:8000"
    c4d_root: Path = Path(r"C:\BKC4D")
    ffmpeg_path: Path = Path(r"C:\Users\oyxw\bin\ffmpeg\ffmpeg.exe")
    openclaw_bin: str = "openclaw"

    orchestrator_host: str = "127.0.0.1"
    orchestrator_port: int = 8765
    pipeline_mode: str = "mock"
    jobs_dir: Path = Path("data/jobs")
    data_root: Path = Path("data")
    c4d_project_template: Path | None = None

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "orchestrator"
    mysql_password: str = "orchestrator"
    mysql_database: str = "ai_video"
    redis_url: str = "redis://127.0.0.1:6379/0"
    qdrant_url: str = "http://127.0.0.1:6333"

    database_url: str = ""
    postgres_url: str = ""

    rag_knowledge_dir: Path = Path("data/knowledge")
    rag_cache_dir: Path = Path("data/rag_cache")
    rag_chroma_dir: Path = Path("data/chroma_db")
    rag_auto_ingest_crawl: bool = True
    rag_bootstrap_on_startup: bool = True

    # ── DeepSeek AI ─────────────────────────────────────────────────────────
    deepseek_api_key: str = ""

    # ── Zhipu (智谱) AI ────────────────────────────────────────────────────
    zhipu_api_key: str = ""
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    zhipu_text_model: str = "GLM-4-Flash"       # 免费文本模型
    zhipu_reasoning_model: str = "GLM-Z1-Flash"  # 免费推理模型（L6 质检）
    zhipu_vision_model: str = "GLM-4.6V-Flash"   # 免费多模态（L1 商品图）
    cogvideo_model: str = "cogvideox-3"           # CogVideoX-3 视频生成
    cogvideo_quality: str = "speed"               # speed | quality
    cogvideo_duration: int = 5                    # 5 | 10 秒
    cogvideo_size: str = "1920x1080"
    cogvideo_poll_max_seconds: int = 600           # 轮询超时（10 分钟）
    cogvideo_poll_interval: int = 5                # 轮询间隔（秒）

    @property
    def c4d_commandline(self) -> Path:
        return self.c4d_root / "Commandline.exe"


settings = Settings()
