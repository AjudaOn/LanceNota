from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import login_user, logout_user
from werkzeug.security import check_password_hash

from ..models import Professor

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/login")
def login():
    return render_template("auth/login.html")


@auth_bp.post("/login")
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    senha = request.form.get("senha") or ""

    if not email or not senha:
        return render_template("auth/login.html", error="Informe email e senha."), 400

    professor = Professor.query.filter_by(email=email).first()
    if professor is None or not check_password_hash(professor.senha_hash, senha):
        return render_template("auth/login.html", error="Email ou senha inválidos."), 401

    login_user(professor)
    return redirect(url_for("pages.dashboard"))


@auth_bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
