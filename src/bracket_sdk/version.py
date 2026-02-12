from importlib import metadata

_PACKAGE_NAME = "bracket-style-sdk"
_FALLBACK_VERSION = "0.1.0"


def _resolve_version() -> str:
    try:
        return metadata.version(_PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return _FALLBACK_VERSION


__version__ = _resolve_version()
