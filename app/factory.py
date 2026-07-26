"""Flask application factory."""
from flask import Flask
from .config import Config
from .extensions import db, migrate, csrf
from .version import get_version


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
        from .repositories import migrate_component_images_to_photos
        migrate_component_images_to_photos()

    # register blueprints (organized by domain following SOLID principles)
    from .routes import register_blueprints
    register_blueprints(app)

    # Add version to template context
    @app.context_processor
    def inject_version():
        return {'app_version': get_version()}

    return app
