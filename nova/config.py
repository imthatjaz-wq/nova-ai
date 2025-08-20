from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict


class Settings(BaseModel):
    """Application settings loaded from environment with safe defaults.

    We avoid implicit writes; data_dir is read for now; modules using it must
    apply permission gates before writes.
    """

    env: str = Field(default_factory=lambda: os.getenv("NOVA_ENV", "development"))
    data_dir: Path = Field(default_factory=lambda: Path(os.getenv("NOVA_DATA_DIR", r"C:\\Nova\\data")))
    log_level: str = Field(default_factory=lambda: os.getenv("NOVA_LOG_LEVEL", "INFO"))

    # Internet / Search
    search_provider: str = Field(default_factory=lambda: os.getenv("NOVA_SEARCH_PROVIDER", "bing"))
    search_api_key: str | None = Field(default_factory=lambda: os.getenv("NOVA_SEARCH_API_KEY"))
    safesearch: str = Field(default_factory=lambda: os.getenv("NOVA_SAFESEARCH", "on"))
    domain_allowlist: str = Field(default_factory=lambda: os.getenv("NOVA_DOMAIN_ALLOWLIST", "wiki,wikipedia,edu,gov"))
    http_rate_limit_per_min: int = Field(default_factory=lambda: int(os.getenv("NOVA_HTTP_RATE_LIMIT_PER_MIN", "30")))

    # CLI
    cli_color: bool = Field(default_factory=lambda: os.getenv("NOVA_CLI_COLOR", "true").lower() in ("1", "true", "yes", "on"))

    # Pydantic v2 style config
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"
