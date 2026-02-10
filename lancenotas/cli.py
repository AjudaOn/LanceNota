import click
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import Professor


@click.command("create-professor")
@click.option("--nome", required=True, help="Nome do professor")
@click.option("--email", required=True, help="Email do professor")
@click.option("--senha", required=True, help="Senha em texto (será hasheada)")
def create_professor_command(nome: str, email: str, senha: str) -> None:
    email_normalized = email.strip().lower()

    existing = Professor.query.filter_by(email=email_normalized).first()
    if existing is not None:
        raise click.ClickException("Já existe um professor com esse email.")

    professor = Professor(
        nome=nome.strip(),
        email=email_normalized,
        senha_hash=generate_password_hash(senha),
    )
    db.session.add(professor)
    db.session.commit()

    click.echo(f"Professor criado: {professor.email} (id={professor.id})")
