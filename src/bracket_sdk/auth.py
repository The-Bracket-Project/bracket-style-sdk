from typing import Optional

API_KEY_HEADER = "x-api-key"
CLIENT_ID_HEADER = "x-client-id"


def apply_auth_headers(headers: Optional[dict], api_key: str, client_id: Optional[str]) -> dict:
    updated = dict(headers) if headers else {}
    if api_key:
        updated[API_KEY_HEADER] = api_key
    if client_id:
        updated[CLIENT_ID_HEADER] = client_id
    return updated
