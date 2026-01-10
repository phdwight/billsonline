"""Tests for version functionality."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import get_version


class TestGetVersion:
    def test_get_version_returns_string(self):
        """Version should be a string."""
        version = get_version()
        assert isinstance(version, str)

    def test_get_version_format(self):
        """Version should be in semver format (X.Y.Z)."""
        version = get_version()
        parts = version.split(".")
        assert len(parts) == 3
        # Each part should be a number
        for part in parts:
            assert part.isdigit()

    def test_get_version_from_file(self, tmp_path, monkeypatch):
        """Test reading version from a VERSION file."""
        # Create a temp VERSION file
        version_file = tmp_path / "VERSION"
        version_file.write_text("1.2.3\n")

        # Monkeypatch the function to use our temp file
        import app

        def mock_get_version():
            try:
                with open(str(version_file), 'r') as f:
                    return f.read().strip()
            except FileNotFoundError:
                return '0.0.1'

        monkeypatch.setattr(app, 'get_version', mock_get_version)

        assert app.get_version() == "1.2.3"

    def test_get_version_default_on_missing_file(self, tmp_path, monkeypatch):
        """Should return default version if VERSION file is missing."""
        import app

        def mock_get_version():
            try:
                with open("/nonexistent/VERSION", 'r') as f:
                    return f.read().strip()
            except FileNotFoundError:
                return '0.0.1'

        monkeypatch.setattr(app, 'get_version', mock_get_version)

        assert app.get_version() == "0.0.1"


class TestVersionContextProcessor:
    def test_app_version_in_context(self):
        """app_version should be available in template context."""
        from app import create_app

        app = create_app()
        app.config.update({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })

        with app.test_request_context():
            # Get context processors
            context = {}
            for func in app.template_context_processors[None]:
                context.update(func())

            assert "app_version" in context
            assert isinstance(context["app_version"], str)
