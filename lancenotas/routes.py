from flask import Flask

from .views.auth import auth_bp
from .views.pages import pages_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)

