#!/usr/bin/env python3
"""
Genera el hash de la contraseña para configurar APP_PASSWORD_HASH.

Uso:
    python generar_hash.py

Copia la línea resultante y agrégala a tu archivo .env o a las
variables de entorno de PythonAnywhere.
"""
from werkzeug.security import generate_password_hash

def main():
    import getpass
    contrasena = getpass.getpass("Ingresa la contraseña que quieres usar: ")
    confirmacion = getpass.getpass("Confirma la contraseña: ")
    if contrasena != confirmacion:
        print("ERROR: Las contraseñas no coinciden.")
        return
    if not contrasena:
        print("ERROR: La contraseña no puede estar vacía.")
        return
    hash_val = generate_password_hash(contrasena)
    print("\nAgrega esto a tu .env o variables de entorno:")
    print(f"APP_PASSWORD_HASH={hash_val}")

if __name__ == "__main__":
    main()

