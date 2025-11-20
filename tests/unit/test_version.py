"""Unit tests for agent version management."""

import re

import pytest


@pytest.mark.unit
class TestVersion:
    """Tests for version management."""

    def test_version_import(self):
        """Test that __version__ can be imported."""
        from agent import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_version_format(self):
        """Test that __version__ follows semantic versioning format."""
        from agent import __version__

        # Should be either a semantic version (X.Y.Z) or development version
        # Semantic version: digits.digits.digits (e.g., "0.2.7", "1.0.0")
        # Development version: "0.0.0.dev"
        is_semver = re.match(r"^\d+\.\d+\.\d+$", __version__)
        is_dev = __version__ == "0.0.0.dev"

        assert is_semver or is_dev, f"Version should be semver or dev: {__version__}"

    def test_version_not_hardcoded(self):
        """Test that version is not the old hardcoded value."""
        from agent import __version__

        # Should not be the old hardcoded version
        assert __version__ != "0.1.0", "Version should be read from package metadata, not hardcoded"

    def test_version_read_from_metadata(self):
        """Test that version is read from package metadata."""
        from importlib.metadata import PackageNotFoundError, version

        from agent import __version__

        # When package is installed, should match metadata version
        try:
            metadata_version = version("agent-base")
            assert __version__ == metadata_version
        except PackageNotFoundError:
            # In development mode without installation, should be dev version
            assert __version__ == "0.0.0.dev"
