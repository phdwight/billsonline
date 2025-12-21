import os
from flask import Flask
from .config import Config
from .extensions import db, migrate, csrf


def get_version() -> str:
    """Read version from VERSION file."""
    version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'VERSION')
    try:
        with open(version_file, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return '0.0.1'


def create_app(config_object: type[Config] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or Config())

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    with app.app_context():
        from . import models  # noqa: F401 ensure models are registered
        db.create_all()

    # register blueprints
    from .routes.main import bp as main_bp
    app.register_blueprint(main_bp)

    # Add version to template context
    @app.context_processor
    def inject_version():
        return {'app_version': get_version()}

    return app
