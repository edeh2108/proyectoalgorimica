"""
Capa de persistencia sobre MongoDB Atlas.

A diferencia de un archivo SQLite local (que se borra cada vez que
Streamlit Cloud reinicia el contenedor), MongoDB Atlas en su capa
gratuita M0 es un clúster siempre activo: los datos quedan guardados
de forma permanente, sin límite de tiempo y sin pausas automáticas.

Requiere una variable de conexión en `st.secrets["MONGODB_URI"]`
(ver README.md para el paso a paso de creación del clúster gratuito).

Colecciones:
    pacientes    -> identificado por dni (string)
    citas        -> id autoincremental propio (via counters)
    pendientes   -> id autoincremental propio (via counters)
    suspendidos  -> identificado por dni (string)
    counters     -> contadores internos para ids autoincrementales
"""

import functools

import streamlit as st
from pymongo import MongoClient, ASCENDING, ReturnDocument
from pymongo.errors import (
    ConfigurationError,
    ConnectionFailure,
    PyMongoError,
    ServerSelectionTimeoutError,
)
from datetime import datetime, timedelta


# Manejo de errores 

def _handle_db_errors(default_return=None):
    """Decorador que evita que un fallo de conexión/escritura en Mongo
    tumbe la app con un traceback crudo. Muestra un mensaje claro con
    st.error() y devuelve un valor por defecto seguro (p. ej. [] para
    listados o None/False para operaciones de escritura)."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except PyMongoError as e:
                st.error(
                    "⚠️ No se pudo completar la operación en la base de datos. "
                    "Puede deberse a un corte de red o a un problema temporal con "
                    "MongoDB Atlas. Vuelve a intentarlo en unos segundos.\n\n"
                    f"Detalle técnico: {e}"
                )
                return default_return

        return wrapper

    return decorator


# Conexión 

@st.cache_resource
def get_client():
    try:
        uri = st.secrets["MONGODB_URI"]
    except Exception:
        st.error(
            "No se encontró la variable MONGODB_URI en los secrets de Streamlit. "
            "Revisa el README.md para configurar tu clúster de MongoDB Atlas."
        )
        st.stop()

    try:
        # serverSelectionTimeoutMS evita que la app se quede "colgada" 30s+
        # si la URI, el usuario/contraseña o el acceso de red están mal
        # configurados; en su lugar falla rápido con un mensaje claro.
        client = MongoClient(uri, serverSelectionTimeoutMS=8000)
        client.admin.command("ping")  # fuerza la conexión ahora, no en el primer guardado
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        st.error(
            "⚠️ No se pudo conectar a MongoDB Atlas. Verifica que:\n\n"
            "1. Tu `MONGODB_URI` en los secrets sea correcta.\n"
            "2. El usuario y contraseña de la base de datos sean válidos.\n"
            "3. En **Network Access** de Atlas tengas habilitado `0.0.0.0/0` "
            "(acceso desde cualquier IP), ya que Streamlit Cloud usa IPs dinámicas.\n\n"
            f"Detalle técnico: {e}"
        )
        st.stop()
    except ConfigurationError as e:
        st.error(
            "⚠️ La cadena de conexión `MONGODB_URI` tiene un formato inválido. "
            f"Revisa que la hayas copiado completa. Detalle técnico: {e}"
        )
        st.stop()
    return client


def get_db():
    return get_client()["citas_medicas"]


def _clean(doc):
    """Quita el _id interno de Mongo antes de exponer el documento a la app."""
    if doc is not None and "_id" in doc:
        doc.pop("_id")
    return doc


def _clean_many(docs):
    return [_clean(d) for d in docs]


@_handle_db_errors()
def init_db():
    d = get_db()
    d.pacientes.create_index("dni", unique=True)
    d.citas.create_index([("especialidad", ASCENDING), ("fecha", ASCENDING), ("hora", ASCENDING)])
    d.citas.create_index("dni")
    d.pendientes.create_index("dni")
    d.suspendidos.create_index("dni", unique=True)


@_handle_db_errors(default_return=False)
def reset_db():
    """Elimina TODOS los documentos de todas las colecciones (pacientes,
    citas, pendientes, suspendidos y contadores internos) para dejar la
    base de datos como recién creada. Esta acción es irreversible."""
    d = get_db()
    for coleccion in ["pacientes", "citas", "pendientes", "suspendidos", "counters"]:
        d[coleccion].delete_many({})
    return True


def _next_id(nombre_contador: str) -> int:
    d = get_db()
    doc = d.counters.find_one_and_update(
        {"_id": nombre_contador},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc["seq"]


# Pacientes 

@_handle_db_errors(default_return=False)
def registrar_paciente(dni, nombres, apellidos, edad, tipo_paciente):
    d = get_db()
    d.pacientes.update_one(
        {"dni": dni},
        {"$set": {
            "dni": dni, "nombres": nombres, "apellidos": apellidos,
            "edad": edad, "tipo_paciente": tipo_paciente,
            "creado_en": datetime.now().isoformat(),
        }},
        upsert=True,
    )
    return True


@_handle_db_errors(default_return=[])
def listar_pacientes():
    d = get_db()
    rows = list(d.pacientes.find().sort("creado_en", -1))
    return _clean_many(rows)


@_handle_db_errors(default_return=None)
def obtener_paciente(dni):
    d = get_db()
    return _clean(d.pacientes.find_one({"dni": dni}))


# Citas 

@_handle_db_errors(default_return=False)
def existe_conflicto_horario(especialidad, fecha, hora, excluir_id=None):
    d = get_db()
    q = {"especialidad": especialidad, "fecha": fecha, "hora": hora, "estado": "confirmada"}
    if excluir_id is not None:
        q["id"] = {"$ne": excluir_id}
    return d.citas.count_documents(q) > 0


@_handle_db_errors(default_return=None)
def crear_cita(dni, especialidad, fecha, hora, nivel_prioridad="IV", puntaje=0):
    d = get_db()
    nuevo_id = _next_id("cita_id")
    d.citas.insert_one({
        "id": nuevo_id, "dni": dni, "especialidad": especialidad, "fecha": fecha,
        "hora": hora, "nivel_prioridad": nivel_prioridad, "puntaje": puntaje,
        "estado": "confirmada", "creado_en": datetime.now().isoformat(),
    })
    return nuevo_id


@_handle_db_errors(default_return=[])
def listar_citas(estado=None):
    d = get_db()
    filtro = {"estado": estado} if estado else {}
    rows = _clean_many(list(d.citas.find(filtro)))
    orden_nivel = {"I": 0, "II": 1, "III": 2, "IV": 3}
    return sorted(rows, key=lambda r: (orden_nivel.get(r["nivel_prioridad"], 3), r["fecha"], r["hora"]))


@_handle_db_errors(default_return=[])
def buscar_citas_por_dni(dni):
    d = get_db()
    return _clean_many(list(d.citas.find({"dni": dni, "estado": "confirmada"})))


@_handle_db_errors(default_return=False)
def cancelar_cita(cita_id):
    d = get_db()
    d.citas.update_one({"id": cita_id}, {"$set": {"estado": "cancelada"}})
    return True


@_handle_db_errors(default_return=False)
def reprogramar_cita(cita_id, nueva_fecha, nueva_hora):
    d = get_db()
    d.citas.update_one({"id": cita_id}, {"$set": {"fecha": nueva_fecha, "hora": nueva_hora}})
    return True


@_handle_db_errors(default_return=[])
def horarios_ocupados(especialidad, fecha):
    d = get_db()
    rows = d.citas.find({"especialidad": especialidad, "fecha": fecha, "estado": "confirmada"})
    return [r["hora"] for r in rows]


# Pre-citas pendientes (panel del cliente) 

@_handle_db_errors(default_return=None)
def crear_pendiente(dni, nombres, apellidos, edad, especialidad, fecha_preferida,
                     contacto, sintomas, nivel_prioridad, puntaje):
    d = get_db()
    nuevo_id = _next_id("pendiente_id")
    d.pendientes.insert_one({
        "id": nuevo_id, "dni": dni, "nombres": nombres, "apellidos": apellidos,
        "edad": edad, "especialidad": especialidad, "fecha_preferida": fecha_preferida,
        "contacto": contacto, "sintomas": sintomas, "nivel_prioridad": nivel_prioridad,
        "puntaje": puntaje, "creado_en": datetime.now().isoformat(),
    })
    return nuevo_id


@_handle_db_errors(default_return=[])
def listar_pendientes():
    d = get_db()
    rows = _clean_many(list(d.pendientes.find()))
    orden_nivel = {"I": 0, "II": 1, "III": 2, "IV": 3}
    return sorted(rows, key=lambda r: (orden_nivel.get(r["nivel_prioridad"], 3), r["creado_en"]))


@_handle_db_errors(default_return=False)
def eliminar_pendiente(pendiente_id):
    d = get_db()
    d.pendientes.delete_one({"id": pendiente_id})
    return True


# Blacklisting / sanciones (sección 2.2.1)

@_handle_db_errors(default_return=False)
def sancionar_dni(dni, motivo, meses):
    d = get_db()
    fecha_sancion = datetime.now()
    fecha_expiracion = fecha_sancion + timedelta(days=30 * meses)
    d.suspendidos.update_one(
        {"dni": dni},
        {"$set": {
            "dni": dni, "motivo": motivo,
            "fecha_sancion": fecha_sancion.isoformat(),
            "fecha_expiracion": fecha_expiracion.isoformat(),
        }},
        upsert=True,
    )
    return True


@_handle_db_errors(default_return=None)
def esta_suspendido(dni):
    """Búsqueda en la lista de suspendidos. Auto-purga sanciones expiradas."""
    d = get_db()
    row = d.suspendidos.find_one({"dni": dni})
    if not row:
        return None
    if datetime.fromisoformat(row["fecha_expiracion"]) < datetime.now():
        d.suspendidos.delete_one({"dni": dni})
        return None
    return _clean(row)


@_handle_db_errors(default_return=[])
def listar_suspendidos():
    d = get_db()
    rows = _clean_many(list(d.suspendidos.find().sort("fecha_sancion", -1)))
    return rows


@_handle_db_errors(default_return=False)
def levantar_sancion(dni):
    d = get_db()
    d.suspendidos.delete_one({"dni": dni})
    return True


def storage_backend_label():
    return "💾 Datos almacenados en MongoDB Atlas (persistencia permanente)"
