"""Blueprint registration for Flask app."""
from .home import bp as home_bp
from .admin import bp as admin_bp
from .participants import bp as participants_bp
from .months import bp as months_bp
from .components import bp as components_bp
from .adjustments import bp as adjustments_bp
from .settings import bp as settings_bp
from .reports import bp as reports_bp


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    app.register_blueprint(home_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(participants_bp)
    app.register_blueprint(months_bp)
    app.register_blueprint(components_bp)
    app.register_blueprint(adjustments_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(reports_bp)
