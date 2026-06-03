"""Script de carga inicial de usuarios.

Ejecutar con: docker compose exec backend python seed.py
Inserta los usuarios base si no existen (verifica por email).
"""

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import RolUsuario, User

# Usuarios base del sistema
USUARIOS = [
    {
        "email": "marcela@yuda.com",
        "password": "admin2025",
        "nombre": "Marcela Arcila",
        "rol": RolUsuario.admin,
    },
    {
        "email": "erika@yuda.com",
        "password": "vendedora2025",
        "nombre": "Erika",
        "rol": RolUsuario.vendedora,
    },
    {
        "email": "daniela@yuda.com",
        "password": "contadora2025",
        "nombre": "Daniela",
        "rol": RolUsuario.contadora,
    },
]


def main() -> None:
    db = SessionLocal()
    insertados = 0
    existentes = 0
    try:
        for datos in USUARIOS:
            existe = db.query(User).filter(User.email == datos["email"]).first()
            if existe:
                existentes += 1
                continue
            usuario = User(
                email=datos["email"],
                nombre=datos["nombre"],
                hashed_password=hash_password(datos["password"]),
                rol=datos["rol"],
            )
            db.add(usuario)
            insertados += 1
        db.commit()
    finally:
        db.close()

    print(f"Usuarios insertados: {insertados}")
    print(f"Usuarios que ya existían: {existentes}")


if __name__ == "__main__":
    main()
