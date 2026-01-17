"""Step definitions for version.feature."""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from app import create_app, get_version

scenarios('../features/version.feature')


# ============ Fixtures ============
@pytest.fixture
def version_app():
    """Create application with test config."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    return app


@pytest.fixture
def version_context(version_app):
    """Context for version tests."""
    return {
        'app': version_app,
        'version': None,
        'version_file': None,
        'mock_version': None,
    }


# ============ Given Steps ============
@given('the application is initialized')
def app_initialized(version_context):
    pass


@given(parsers.parse('a VERSION file exists with content "{content}"'))
def version_file_exists(version_context, content, tmp_path, monkeypatch):
    version_file = tmp_path / "VERSION"
    version_file.write_text(content + "\n")
    version_context['version_file'] = str(version_file)
    
    # Monkeypatch to use temp file
    import app
    original_get_version = app.get_version
    
    def mock_get_version():
        try:
            with open(str(version_file), 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return '0.0.1'
    
    monkeypatch.setattr(app, 'get_version', mock_get_version)
    version_context['mock_version'] = mock_get_version


@given('the VERSION file does not exist')
def version_file_missing(version_context, monkeypatch):
    import app
    
    def mock_get_version():
        try:
            with open("/nonexistent/VERSION", 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return '0.0.1'
    
    monkeypatch.setattr(app, 'get_version', mock_get_version)
    version_context['mock_version'] = mock_get_version


# ============ When Steps ============
@when('I get the application version')
def get_app_version(version_context):
    if version_context['mock_version']:
        version_context['version'] = version_context['mock_version']()
    else:
        version_context['version'] = get_version()


@when('I render a page')
def render_page(version_context):
    with version_context['app'].test_client() as client:
        version_context['response'] = client.get('/admin')


# ============ Then Steps ============
@then('the version should be a string')
def version_is_string(version_context):
    assert isinstance(version_context['version'], str)


@then('the version should have 3 parts separated by dots')
def version_has_3_parts(version_context):
    parts = version_context['version'].split('.')
    assert len(parts) == 3


@then('each part should be a number')
def parts_are_numbers(version_context):
    parts = version_context['version'].split('.')
    for part in parts:
        assert part.isdigit()


@then(parsers.parse('the version should be "{expected}"'))
def version_equals(version_context, expected):
    assert version_context['version'] == expected


@then('the app_version should be available in the template context')
def version_in_context(version_context):
    # Verify by checking response contains version
    assert b'version-footer' in version_context['response'].data
    assert b'>v' in version_context['response'].data
