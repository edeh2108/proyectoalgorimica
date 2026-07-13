"""
Script independiente para vaciar la base de datos "citas_medicas" en tu
clúster real de MongoDB Atlas y dejarla como recién creada (sin pacientes,
citas, pendientes, sanciones ni contadores).

NO se ejecuta dentro de la app de Streamlit: es un script de un solo uso
que corres tú mismo, una vez, apuntando a tu propio MONGODB_URI.

Uso:
    1. Activa tu entorno virtual e instala las dependencias si no lo has
       hecho: pip install -r requirements.txt
    2. Ejecuta:
           python reset_db.py "mongodb+srv://usuario:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority"
       O, si ya tienes MONGODB_URI como variable de entorno:
           export MONGODB_URI="mongodb+srv://..."
           python reset_db.py
    3. Escribe "REINICIAR" cuando se te pida confirmar.

Nota: si prefieres no usar la terminal, la misma opción ya está disponible
dentro de la app, en el Panel administrativo → "⚠️ Zona de peligro —
Reiniciar base de datos".
"""

import os
import sys

from pymongo import MongoClient


def main():
    uri = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MONGODB_URI")
    if not uri:
        print(
            "❌ No se encontró la URI de conexión.\n"
            "Pásala como argumento: python reset_db.py \"mongodb+srv://...\"\n"
            "o expórtala como variable de entorno MONGODB_URI."
        )
        sys.exit(1)

    print("Conectando a MongoDB Atlas...")
    client = MongoClient(uri, serverSelectionTimeoutMS=8000)
    try:
        client.admin.command("ping")
    except Exception as e:
        print(f"❌ No se pudo conectar: {e}")
        sys.exit(1)

    db = client["citas_medicas"]
    colecciones = ["pacientes", "citas", "pendientes", "suspendidos", "counters"]

    print("\nSe eliminarán TODOS los documentos de las siguientes colecciones:")
    for c in colecciones:
        total = db[c].count_documents({})
        print(f"  - {c}: {total} documento(s)")

    confirmacion = input("\nEscribe REINICIAR para confirmar el borrado permanente: ")
    if confirmacion != "REINICIAR":
        print("Cancelado. No se eliminó nada.")
        sys.exit(0)

    for c in colecciones:
        resultado = db[c].delete_many({})
        print(f"  - {c}: {resultado.deleted_count} documento(s) eliminado(s)")

    print("\n✅ Base de datos reiniciada. Ya no queda ningún DNI suspendido ni registro previo.")


if __name__ == "__main__":
    main()
