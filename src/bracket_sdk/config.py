from dataclasses import dataclass
from typing import Optional

from bracket_sdk.version import __version__

DEFAULT_BASE_URL = "https://api.bracketstyle.com"
DEFAULT_TIMEOUT = 10.0
DEFAULT_RETRIES = 3


@dataclass(frozen=True)
class SDKConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    retries: int = DEFAULT_RETRIES
    user_agent: Optional[str] = None
    client_id: Optional[str] = None

    def user_agent_value(self) -> str:
        if self.user_agent:
            return self.user_agent
        return f"bracket-sdk/{__version__}"
