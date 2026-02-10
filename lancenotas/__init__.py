from flask import Flask

from .config import Settings
from .extensions import db, login_manager, migrate
from .routes import register_blueprints
from .cli import create_professor_command


def create_app() -> Flask:
    from dotenv import load_dotenv  # noqa: PLC0415

    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)
    app.instance_path  # ensure attribute exists
    import os  # noqa: PLC0415

    os.makedirs(app.instance_path, exist_ok=True)
    settings = Settings.from_env()

    database_url = settings.database_url
    if database_url.startswith("sqlite:///instance/"):
        filename = database_url.removeprefix("sqlite:///instance/")
        database_url = f"sqlite:///{os.path.join(app.instance_path, filename)}"

    app.config.update(
        SECRET_KEY=settings.secret_key,
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,  # 8MB
    )

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .models import Professor  # noqa: PLC0415

    @login_manager.user_loader
    def load_user(user_id: str) -> Professor | None:
        try:
            professor_id = int(user_id)
        except ValueError:
            return None
        return db.session.get(Professor, professor_id)

    register_blueprints(app)
    app.cli.add_command(create_professor_command)

    return app
