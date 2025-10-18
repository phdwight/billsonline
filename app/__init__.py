from flask import Flask
from .config import Config
from .extensions import db, migrate, csrf


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

    return app
