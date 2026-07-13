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

import streamlit as st
from pymongo import MongoClient, ASCENDING, ReturnDocument
from datetime import datetime, timedelta



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
    return MongoClient(uri)


def get_db():
    return get_client()["citas_medicas"]


def _clean(doc):
    """Quita el _id interno de Mongo antes de exponer el documento a la app."""
    if doc is not None and "_id" in doc:
        doc.pop("_id")
    return doc


def _clean_many(docs):
    return [_clean(d) for d in docs]


def init_db():
    d = get_db()
    d.pacientes.create_index("dni", unique=True)
    d.citas.create_index([("especialidad", ASCENDING), ("fecha", ASCENDING), ("hora", ASCENDING)])
    d.citas.create_index("dni")
    d.pendientes.create_index("dni")
    d.suspendidos.create_index("dni", unique=True)


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


def listar_pacientes():
    d = get_db()
    rows = list(d.pacientes.find().sort("creado_en", -1))
    return _clean_many(rows)


def obtener_paciente(dni):
    d = get_db()
    return _clean(d.pacientes.find_one({"dni": dni}))


# Citas 

def existe_conflicto_horario(especialidad, fecha, hora, excluir_id=None):
    d = get_db()
    q = {"especialidad": especialidad, "fecha": fecha, "hora": hora, "estado": "confirmada"}
    if excluir_id is not None:
        q["id"] = {"$ne": excluir_id}
    return d.citas.count_documents(q) > 0


def crear_cita(dni, especialidad, fecha, hora, nivel_prioridad="IV", puntaje=0):
    d = get_db()
    nuevo_id = _next_id("cita_id")
    d.citas.insert_one({
        "id": nuevo_id, "dni": dni, "especialidad": especialidad, "fecha": fecha,
        "hora": hora, "nivel_prioridad": nivel_prioridad, "puntaje": puntaje,
        "estado": "confirmada", "creado_en": datetime.now().isoformat(),
    })
    return nuevo_id


def listar_citas(estado=None):
    d = get_db()
    filtro = {"estado": estado} if estado else {}
    rows = _clean_many(list(d.citas.find(filtro)))
    orden_nivel = {"I": 0, "II": 1, "III": 2, "IV": 3}
    return sorted(rows, key=lambda r: (orden_nivel.get(r["nivel_prioridad"], 3), r["fecha"], r["hora"]))


def buscar_citas_por_dni(dni):
    d = get_db()
    return _clean_many(list(d.citas.find({"dni": dni, "estado": "confirmada"})))


def cancelar_cita(cita_id):
    d = get_db()
    d.citas.update_one({"id": cita_id}, {"$set": {"estado": "cancelada"}})


def reprogramar_cita(cita_id, nueva_fecha, nueva_hora):
    d = get_db()
    d.citas.update_one({"id": cita_id}, {"$set": {"fecha": nueva_fecha, "hora": nueva_hora}})


def horarios_ocupados(especialidad, fecha):
    d = get_db()
    rows = d.citas.find({"especialidad": especialidad, "fecha": fecha, "estado": "confirmada"})
    return [r["hora"] for r in rows]


# Pre-citas pendientes (panel del cliente) 

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


def listar_pendientes():
    d = get_db()
    rows = _clean_many(list(d.pendientes.find()))
    orden_nivel = {"I": 0, "II": 1, "III": 2, "IV": 3}
    return sorted(rows, key=lambda r: (orden_nivel.get(r["nivel_prioridad"], 3), r["creado_en"]))


def eliminar_pendiente(pendiente_id):
    d = get_db()
    d.pendientes.delete_one({"id": pendiente_id})


# Blacklisting / sanciones (sección 2.2.1)

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


def listar_suspendidos():
    d = get_db()
    rows = _clean_many(list(d.suspendidos.find().sort("fecha_sancion", -1)))
    return rows


def levantar_sancion(dni):
    d = get_db()
    d.suspendidos.delete_one({"dni": dni})
def storage_backend_label():
       return "💾 Datos almacenados en MongoDB Atlas (persistencia permanente)"
