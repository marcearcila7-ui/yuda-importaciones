"""Script de carga inicial de usuarios.

Ejecutar con: python seed.py  (o docker compose exec backend python seed.py)
Inserta los usuarios base si no existen (verifica por email).

Las contraseñas se toman de variables de entorno; si alguna no está definida, se
genera una aleatoria segura y se imprime UNA sola vez para que la guardes. Nunca
hay contraseñas por defecto hardcodeadas en el código.

Variables: SEED_ADMIN_PASSWORD, SEED_VENDEDORA_PASSWORD, SEED_CONTADORA_PASSWORD
"""
import os
import secrets

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import RolUsuario, User

# (email, variable de entorno para la contraseña, nombre, rol)
USUARIOS = [
    ("marcela@yuda.com", "SEED_ADMIN_PASSWORD", "Marcela Arcila", RolUsuario.admin),
    ("erika@yuda.com", "SEED_VENDEDORA_PASSWORD", "Erika", RolUsuario.vendedora),
    ("daniela@yuda.com", "SEED_CONTADORA_PASSWORD", "Daniela", RolUsuario.contadora),
]


def _password(env_var: str, generadas: dict) -> str:
    """Devuelve la contraseña de la variable de entorno, o una aleatoria segura
    (recordándola en `generadas` para imprimirla al final)."""
    valor = os.environ.get(env_var)
    if valor:
        return valor
    generada = secrets.token_urlsafe(12)
    generadas[env_var] = generada
    return generada


def main() -> None:
    db = SessionLocal()
    insertados = 0
    existentes = 0
    generadas: dict[str, str] = {}
    try:
        for email, env_var, nombre, rol in USUARIOS:
            if db.query(User).filter(User.email == email).first():
                existentes += 1
                continue
            usuario = User(
                email=email,
                nombre=nombre,
                hashed_password=hash_password(_password(env_var, generadas)),
                rol=rol,
            )
            db.add(usuario)
            insertados += 1
        db.commit()
    finally:
        db.close()

    print(f"Usuarios insertados: {insertados}")
    print(f"Usuarios que ya existían: {existentes}")
    if generadas:
        print("\n⚠️  Contraseñas generadas (guárdalas ahora, NO se vuelven a mostrar):")
        for env_var, valor in generadas.items():
            print(f"  {env_var} → {valor}")


if __name__ == "__main__":
    main()
