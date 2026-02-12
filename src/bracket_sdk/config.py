from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from bracket_sdk.version import __version__

DEFAULT_BASE_URL = "https://api-sdk.demo.thebracket.ai"
DEFAULT_TIMEOUT = 10.0
DEFAULT_RETRIES = 3
DEFAULT_ALLOW_NON_IDEMPOTENT_RETRIES = False
DEFAULT_RESPECT_RETRY_AFTER = True
DEFAULT_JITTER = False
DEFAULT_RETRY_AFTER_MAX_SECONDS = 30.0

HookCallback = Callable[[Dict[str, Any]], None]


@dataclass(frozen=True)
class SDKConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    retries: int = DEFAULT_RETRIES
    user_agent: Optional[str] = None
    client_id: Optional[str] = None
    allow_non_idempotent_retries: bool = DEFAULT_ALLOW_NON_IDEMPOTENT_RETRIES
    respect_retry_after: bool = DEFAULT_RESPECT_RETRY_AFTER
    # Keep jitter disabled by default for deterministic behavior in clients/tests.
    jitter: bool = DEFAULT_JITTER
    retry_after_max_seconds: float = DEFAULT_RETRY_AFTER_MAX_SECONDS
    # Hook exceptions are propagated to the caller.
    on_request: Optional[HookCallback] = None
    on_response: Optional[HookCallback] = None
    on_retry: Optional[HookCallback] = None

    def user_agent_value(self) -> str:
        if self.user_agent:
            return self.user_agent
        return f"bracket-sdk/{__version__}"
