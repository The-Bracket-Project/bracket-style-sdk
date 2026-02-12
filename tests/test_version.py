from importlib import metadata

from bracket_sdk.version import __version__


def test_runtime_version_matches_package_metadata_or_fallback() -> None:
    fallback = "0.1.0"
    try:
        expected = metadata.version("bracket-style-sdk")
    except metadata.PackageNotFoundError:
        expected = fallback

    assert __version__ == expected
