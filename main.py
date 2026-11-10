"""Punto de entrada del analizador de grafos de Active Directory.

Ejecutar con, por ejemplo:

    python main.py resumen
    python main.py defensa --objetivo "DOMAIN ADMINS@TestCompany.Local"
"""

from grafo_ad.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
