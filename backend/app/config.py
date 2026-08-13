"""Environment-backed application settings."""

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(os.getenv("CYBERSHIELD_DATABASE", "data/cybershield.db"))
    secret_key: str = os.getenv("CYBERSHIELD_SECRET_KEY", "change-me-before-production")
    access_token_hours: int = int(os.getenv("CYBERSHIELD_ACCESS_TOKEN_HOURS", "24"))
    rate_limit_per_minute: int = int(os.getenv("CYBERSHIELD_RATE_LIMIT_PER_MINUTE", "20"))
    virus_total_api_key: str | None = os.getenv("VIRUSTOTAL_API_KEY")
    google_safe_browsing_api_key: str | None = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY")
    model_path: Path = Path(os.getenv("CYBERSHIELD_MODEL_PATH", "models/phishing_model.joblib"))
    # The bundled model is synthetic and must never silently replace the
    # explainable live-evidence baseline. Enable only after model validation.
    use_trained_model: bool = os.getenv("CYBERSHIELD_USE_TRAINED_MODEL", "false").lower() == "true"
    firebase_service_account: Path | None = Path(os.getenv("FIREBASE_SERVICE_ACCOUNT")) if os.getenv("FIREBASE_SERVICE_ACCOUNT") else None


settings = Settings()
