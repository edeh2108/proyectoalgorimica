import streamlit as st
from datetime import date, datetime, timedelta

import db
import priority
from style import CUSTOM_CSS, HEADER_HTML, badge

# ----------------------------------------------------------------------------
# Configuración general
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Sistema de Gestión de Citas Médicas",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.markdown(HEADER_HTML, unsafe_allow_html=True)

db.init_db()

ESPECIALIDADES = [
    "Medicina General", "Pediatría", "Ginecología", "Cardiología",
    "Traumatología", "Dermatología", "Odontología",
]
HORAS_DISPONIBLES = [f"{h:02d}:00" for h in range(6, 18)]

ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123") if hasattr(st, "secrets") else "admin123"


# ----------------------------------------------------------------------------
# Navegación
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Navegación")
    panel = st.radio(
        "Selecciona un panel",
        ["Panel del cliente", "Panel administrativo"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption(db.storage_backend_label())
    st.caption(
        "Motor de prioridad clínica adaptado del Modified Early Warning "
        "Score (MEWS) — Subbe et al. (2001)."
    )


# ============================================================================
# PANEL DEL CLIENTE
# ============================================================================
if panel == "Panel del cliente":

    st.subheader("Solicitud de cita médica")
    st.write(
        "Completa tus datos y el cuestionario de triaje. El sistema calculará "
        "automáticamente tu nivel de prioridad clínica antes de asignarte un turno."
    )

    dni_check = st.text_input("Ingresa tu DNI para comenzar", max_chars=8, key="dni_gate")

    if dni_check:
        suspension = db.esta_suspendido(dni_check)
        if suspension:
            fecha_exp = datetime.fromisoformat(suspension["fecha_expiracion"]).strftime("%d/%m/%Y")
            st.markdown(
                f"""
                <div class="pill-suspendido">
                    🚫 Acceso restringido. Tu DNI se encuentra suspendido del canal digital
                    hasta el <b>{fecha_exp}</b> por motivo de: <i>{suspension["motivo"]}</i>.<br><br>
                    Si se trata de una <b>emergencia real</b>, acércate presencialmente a las
                    ventanillas de triaje físico de la clínica; no es necesario el canal web
                    para ser atendido.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            with st.form("form_pre_cita"):
                col1, col2 = st.columns(2)
                with col1:
                    nombres = st.text_input("Nombres")
                    edad = st.number_input("Edad", min_value=0, max_value=120, step=1)
                    especialidad = st.selectbox("Especialidad médica", ESPECIALIDADES)
                    contacto = st.text_input("Teléfono o correo de contacto")
                with col2:
                    apellidos = st.text_input("Apellidos")
                    gestante = st.checkbox("¿Actualmente gestante?")
                    fecha_preferida = st.date_input("Fecha preferida", min_value=date.today())

                st.markdown("##### Cuestionario de triaje")
                c1, c2 = st.columns(2)
                with c1:
                    dificultad = st.selectbox(
                        "Dificultad respiratoria", list(priority.ESCALA_RESPIRATORIA.keys())
                    )
                    temperatura = st.selectbox(
                        "Temperatura corporal", list(priority.ESCALA_TEMPERATURA.keys())
                    )
                with c2:
                    conciencia = st.selectbox(
                        "Estado de conciencia", list(priority.ESCALA_CONCIENCIA.keys())
                    )
                    dolor = st.selectbox(
                        "Dolor (Escala EVA)", list(priority.ESCALA_DOLOR.keys())
                    )

                sintomas_extra = st.text_area(
                    "Describe brevemente el motivo de tu consulta (opcional)"
                )

                enviado = st.form_submit_button("Calcular prioridad y enviar solicitud", type="primary")

            if enviado:
                if not (nombres and apellidos and contacto):
                    st.error("Completa nombres, apellidos y un contacto antes de continuar.")
                else:
                    resultado = priority.calcular_prioridad(
                        dificultad, conciencia, temperatura, dolor, int(edad), gestante
                    )
                    pendiente_id = db.crear_pendiente(
                        dni_check, nombres, apellidos, int(edad), especialidad,
                        fecha_preferida.isoformat(), contacto, sintomas_extra,
                        resultado.nivel, resultado.puntaje_total,
                    )
                    if pendiente_id is not None:
                        st.success("Tu solicitud fue registrada y está pendiente de evaluación por el personal.")
                        st.markdown(
                            f"""
                            <div class="card">
                                <b>Resultado de tu triaje</b><br><br>
                                {badge(resultado.nivel, resultado.etiqueta)}<br><br>
                                Puntaje total (P_total): <b>{resultado.puntaje_total}</b><br>
                                Manejo de cola: {resultado.posicion_cola}<br>
                                Tiempo sugerido de atención: {resultado.tiempo_sugerido}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.info(
                            "El personal administrativo confirmará tu cita según disponibilidad "
                            "de horarios. Puedes cerrar esta ventana."
                        )
                    # Si pendiente_id es None, db.py ya mostró el error de guardado
                    # y la solicitud NO quedó registrada; el usuario debe reintentar.

    st.markdown("---")
    with st.expander("Consultar mis citas confirmadas"):
        dni_consulta = st.text_input("DNI", key="dni_consulta")
        if dni_consulta:
            citas = db.buscar_citas_por_dni(dni_consulta)
            if citas:
                for c in citas:
                    st.markdown(
                        f"""
                        <div class="card">
                            <b>{c["especialidad"]}</b> — {c["fecha"]} a las {c["hora"]}<br>
                            {badge(c["nivel_prioridad"], "Prioridad " + c["nivel_prioridad"])}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.write("No se encontraron citas confirmadas para este DNI.")


# ============================================================================
# PANEL ADMINISTRATIVO
# ============================================================================
else:
    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False

    if not st.session_state.admin_ok:
        st.subheader("Acceso del personal administrativo")
        clave = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", type="primary"):
            if clave == ADMIN_PASSWORD:
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        st.stop()

    tabs = st.tabs([
        "Solicitudes pendientes", "Registro de pacientes", "Agendar cita",
        "Agenda / Cola de prioridad", "Cancelar o reprogramar", "Lista de suspendidos",
    ])

    # ---- Solicitudes pendientes (evaluación de triaje) ----
    with tabs[0]:
        st.subheader("Bandeja de pre-citas pendientes")
        pendientes = db.listar_pendientes()
        if not pendientes:
            st.write("No hay solicitudes pendientes por evaluar.")
        for p in pendientes:
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(
                        f"**{p['nombres']} {p['apellidos']}** — DNI: {p['dni']} — "
                        f"Edad: {p['edad']}<br>"
                        f"Especialidad: {p['especialidad']} · Fecha preferida: {p['fecha_preferida']}<br>"
                        f"Contacto: {p['contacto']}<br>"
                        f"Motivo: {p['sintomas'] or '—'}<br>"
                        f"{badge(p['nivel_prioridad'], 'Prioridad ' + p['nivel_prioridad'])} "
                        f"(P_total = {p['puntaje']})",
                        unsafe_allow_html=True,
                    )
                with col2:
                    hora_asignada = st.selectbox(
                        "Hora", HORAS_DISPONIBLES, key=f"hora_{p['id']}"
                    )
                    aceptar = st.button("✅ Aceptar y confirmar cita", key=f"ok_{p['id']}")
                    rechazar = st.button("❌ Rechazar solicitud", key=f"no_{p['id']}")

                if aceptar:
                    if db.existe_conflicto_horario(p["especialidad"], p["fecha_preferida"], hora_asignada):
                        st.error("Ese horario ya está ocupado. Elige otra hora.")
                    else:
                        if not db.obtener_paciente(p["dni"]):
                            tipo = "adulto_mayor" if p["edad"] > 60 else "normal"
                            db.registrar_paciente(p["dni"], p["nombres"], p["apellidos"], p["edad"], tipo)
                        nuevo_id = db.crear_cita(
                            p["dni"], p["especialidad"], p["fecha_preferida"], hora_asignada,
                            p["nivel_prioridad"], p["puntaje"],
                        )
                        if nuevo_id is not None:
                            db.eliminar_pendiente(p["id"])
                            st.success("Cita confirmada.")
                            st.rerun()
                        # Si nuevo_id es None, db.py ya mostró el error de conexión/guardado.

                if rechazar:
                    st.session_state[f"rechazando_{p['id']}"] = True

                if st.session_state.get(f"rechazando_{p['id']}"):
                    motivo = st.text_input(
                        "Motivo del rechazo (fraude, datos falsos, duplicado, etc.)",
                        key=f"motivo_{p['id']}",
                    )
                    meses = st.number_input(
                        "Duración de la suspensión (meses)", min_value=1, max_value=24,
                        value=3, key=f"meses_{p['id']}",
                    )
                    if st.button("Confirmar sanción y eliminar solicitud", key=f"confirmar_no_{p['id']}"):
                        ok = db.sancionar_dni(p["dni"], motivo or "Solicitud fraudulenta o inconsistente", int(meses))
                        if ok:
                            db.eliminar_pendiente(p["id"])
                            st.warning(f"DNI {p['dni']} indexado en la lista de suspendidos por {meses} mes(es).")
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # ---- Registro de pacientes ----
    with tabs[1]:
        st.subheader("Registro de pacientes")
        with st.form("form_paciente"):
            col1, col2 = st.columns(2)
            with col1:
                dni_p = st.text_input("DNI")
                nombres_p = st.text_input("Nombres")
                edad_p = st.number_input("Edad", min_value=0, max_value=120, step=1)
            with col2:
                apellidos_p = st.text_input("Apellidos")
                tipo_p = st.selectbox(
                    "Tipo de paciente", ["normal", "adulto_mayor", "emergencia"]
                )
            guardar = st.form_submit_button("Registrar paciente", type="primary")
        if guardar:
            if dni_p and nombres_p and apellidos_p:
                if db.registrar_paciente(dni_p, nombres_p, apellidos_p, int(edad_p), tipo_p):
                    st.success("Paciente registrado correctamente.")
                # Si falla, db.py ya mostró el mensaje de error correspondiente.
            else:
                st.error("DNI, nombres y apellidos son obligatorios.")

        st.markdown("##### Pacientes registrados")
        pacientes = db.listar_pacientes()
        if pacientes:
            st.dataframe(
                [dict(r) for r in pacientes],
                use_container_width=True, hide_index=True,
            )
        else:
            st.write("Aún no hay pacientes registrados.")

    # ---- Agendar cita ----
    with tabs[2]:
        st.subheader("Agendamiento manual de citas")
        pacientes = db.listar_pacientes()
        if not pacientes:
            st.info("Registra al menos un paciente antes de agendar una cita.")
        else:
            opciones = {f"{p['nombres']} {p['apellidos']} ({p['dni']})": p["dni"] for p in pacientes}
            with st.form("form_cita"):
                seleccion = st.selectbox("Paciente", list(opciones.keys()))
                especialidad_c = st.selectbox("Especialidad médica", ESPECIALIDADES, key="esp_agenda")
                fecha_c = st.date_input("Fecha", min_value=date.today(), key="fecha_agenda")
                hora_c = st.selectbox("Hora", HORAS_DISPONIBLES, key="hora_agenda")
                agendar = st.form_submit_button("Verificar disponibilidad y agendar", type="primary")

            if agendar:
                dni_sel = opciones[seleccion]
                if db.existe_conflicto_horario(especialidad_c, fecha_c.isoformat(), hora_c):
                    st.error("Conflicto de horario: ya existe una cita en esa especialidad, fecha y hora.")
                elif db.crear_cita(dni_sel, especialidad_c, fecha_c.isoformat(), hora_c) is not None:
                    st.success("Cita agendada correctamente.")

            st.markdown("##### Disponibilidad del día")
            colA, colB = st.columns(2)
            with colA:
                esp_check = st.selectbox("Especialidad a consultar", ESPECIALIDADES, key="esp_check")
            with colB:
                fecha_check = st.date_input("Fecha a consultar", min_value=date.today(), key="fecha_check")
            ocupadas = db.horarios_ocupados(esp_check, fecha_check.isoformat())
            libres = [h for h in HORAS_DISPONIBLES if h not in ocupadas]
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Horarios libres**")
                st.write(", ".join(libres) if libres else "Sin horarios libres.")
            with c2:
                st.markdown("**Horarios ocupados**")
                st.write(", ".join(ocupadas) if ocupadas else "Ninguno.")

    # ---- Agenda / cola de prioridad ----
    with tabs[3]:
        st.subheader("Agenda general ordenada por prioridad clínica")
        citas = db.listar_citas(estado="confirmada")
        if citas:
            filas = []
            for c in citas:
                filas.append({
                    "ID": c["id"], "DNI": c["dni"], "Especialidad": c["especialidad"],
                    "Fecha": c["fecha"], "Hora": c["hora"],
                    "Prioridad": f"Nivel {c['nivel_prioridad']}", "P_total": c["puntaje"],
                })
            st.dataframe(filas, use_container_width=True, hide_index=True)
        else:
            st.write("No hay citas confirmadas todavía.")

    # ---- Cancelar o reprogramar ----
    with tabs[4]:
        st.subheader("Cancelación y reprogramación de citas")
        dni_buscar = st.text_input("Buscar citas por DNI")
        if dni_buscar:
            citas_dni = db.buscar_citas_por_dni(dni_buscar)
            if not citas_dni:
                st.write("No se encontraron citas activas para ese DNI.")
            for c in citas_dni:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.write(f"Cita #{c['id']} — {c['especialidad']} — {c['fecha']} {c['hora']}")
                col1, col2, col3 = st.columns(3)
                with col1:
                    nueva_fecha = st.date_input("Nueva fecha", min_value=date.today(), key=f"nf_{c['id']}")
                with col2:
                    nueva_hora = st.selectbox("Nueva hora", HORAS_DISPONIBLES, key=f"nh_{c['id']}")
                with col3:
                    st.write("")
                    st.write("")
                    reprogramar = st.button("Reprogramar", key=f"rep_{c['id']}")
                    cancelar = st.button("Cancelar cita", key=f"can_{c['id']}")

                if reprogramar:
                    if db.existe_conflicto_horario(
                        c["especialidad"], nueva_fecha.isoformat(), nueva_hora, excluir_id=c["id"]
                    ):
                        st.error("El nuevo horario ya está ocupado.")
                    elif db.reprogramar_cita(c["id"], nueva_fecha.isoformat(), nueva_hora):
                        st.success("Cita reprogramada.")
                        st.rerun()

                if cancelar:
                    if db.cancelar_cita(c["id"]):
                        st.warning("Cita cancelada.")
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # ---- Lista de suspendidos ----
    with tabs[5]:
        st.subheader("DNIs suspendidos del canal digital")
        st.write(
            "Estos DNIs tienen bloqueado el acceso al panel del cliente hasta la "
            "fecha de expiración indicada. La sanción se levanta automáticamente "
            "al vencer, o puedes levantarla antes manualmente."
        )
        suspendidos = db.listar_suspendidos()
        if not suspendidos:
            st.write("No hay DNIs suspendidos actualmente.")
        else:
            for s in suspendidos:
                fecha_sancion = datetime.fromisoformat(s["fecha_sancion"]).strftime("%d/%m/%Y")
                fecha_exp = datetime.fromisoformat(s["fecha_expiracion"]).strftime("%d/%m/%Y")
                st.markdown('<div class="card">', unsafe_allow_html=True)
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(
                        f"**DNI:** {s['dni']}<br>"
                        f"**Motivo:** {s['motivo']}<br>"
                        f"**Sancionado el:** {fecha_sancion} · **Expira el:** {fecha_exp}",
                        unsafe_allow_html=True,
                    )
                with col2:
                    if st.button("✅ Levantar sanción", key=f"levantar_{s['dni']}"):
                        if db.levantar_sancion(s["dni"]):
                            st.success(f"Sanción del DNI {s['dni']} levantada.")
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("Cerrar sesión"):
            st.session_state.admin_ok = False
            st.rerun()

    with col_b:
        with st.expander("⚠️ Zona de peligro — Reiniciar base de datos"):
            st.write(
                "Esto elimina **permanentemente** todos los pacientes, citas, "
                "solicitudes pendientes y sanciones registradas, dejando la base "
                "de datos como recién creada. **Esta acción no se puede deshacer.**"
            )
            confirmacion = st.text_input(
                "Escribe REINICIAR para confirmar", key="confirmar_reset_db"
            )
            if st.button("Eliminar todos los datos", type="primary", key="btn_reset_db"):
                if confirmacion == "REINICIAR":
                    if db.reset_db():
                        st.success("Base de datos reiniciada. Todos los registros fueron eliminados.")
                        st.rerun()
                else:
                    st.error("Debes escribir exactamente REINICIAR para confirmar.")
