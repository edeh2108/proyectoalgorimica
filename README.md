# Sistema de Gestión de Citas Médicas

Aplicación web (Streamlit + MongoDB Atlas) construida a partir del informe
**"Sistema de gestión de citas médicas"** (UNMSM, Algorítmica I, Grupo 7).

Implementa:

- **Panel administrativo**: registro de pacientes, agendamiento con
  validación de conflictos de horario, búsqueda de disponibilidad,
  cancelación y reprogramación, y bandeja de solicitudes pendientes.
- **Panel del cliente**: formulario de pre-cita con cuestionario de triaje
  que calcula el **Nivel de Prioridad Total** (adaptación del MEWS,
  Subbe et al., 2001) y clasifica al paciente en Prioridad I–IV.
- **Módulo de restricción temprana (blacklisting)**: si el personal
  rechaza una pre-cita por ser fraudulenta o inconsistente, el DNI queda
  suspendido del canal digital por el número de meses que el
  administrador defina, con bloqueo automático en cada nuevo intento y
  auto-expiración de la sanción.
- **Persistencia permanente**: los datos se guardan en **MongoDB Atlas**
  (capa gratuita M0), un clúster que **nunca se apaga ni se reinicia**.
  A diferencia de un archivo SQLite local, aquí los datos sobreviven
  cualquier redeploy, reinicio o inactividad de la app en Streamlit
  Cloud — quedan guardados para siempre.

---

## Estructura del proyecto

```
sistema_citas/
├── app.py                          # Interfaz Streamlit (panel admin + panel cliente)
├── db.py                           # Persistencia en MongoDB Atlas
├── priority.py                     # Motor de prioridad clínica (MEWS adaptado)
├── style.py                        # CSS profesional inyectado en la app
├── requirements.txt
├── .gitignore
└── .streamlit/
    ├── config.toml                 # Tema visual
    └── secrets.toml.example        # Plantilla (NO subir la real a GitHub)
```

---

## Paso 1 — Crear el clúster gratuito en MongoDB Atlas (para siempre, gratis)

1. Entra a **https://www.mongodb.com/cloud/atlas/register** y crea una
   cuenta (puedes usar tu cuenta de Google/GitHub).
2. Al crear el proyecto, elige el plan **M0 Free** (512 MB, gratis de
   forma permanente, sin tarjeta de crédito, sin pausas automáticas).
3. Elige cualquier proveedor/región (por ejemplo AWS, la más cercana a
   Perú suele ser `sa-east-1` São Paulo).
4. **Database Access** (menú izquierdo) → **Add New Database User**:
   crea un usuario y contraseña (guárdalos, los necesitarás en la URI).
5. **Network Access** → **Add IP Address** → selecciona
   **"Allow access from anywhere" (0.0.0.0/0)**. Esto es necesario
   porque Streamlit Cloud usa IPs dinámicas.
6. **Database → Connect → Drivers**: elige **Python**, y copia la
   cadena de conexión. Se ve así:
   ```
   mongodb+srv://usuario:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
   Reemplaza `<password>` por la contraseña real del usuario que creaste.
   Esta cadena completa es tu `MONGODB_URI`.

No necesitas crear manualmente la base de datos ni las colecciones:
`db.init_db()` las crea automáticamente en el primer arranque de la app.

---

## Paso 2 — Probar en tu computadora (opcional, antes de publicar)

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edita `.streamlit/secrets.toml` y pega tu `MONGODB_URI` real. Luego:

```bash
streamlit run app.py
```

Se abrirá `http://localhost:8501`. Todo lo que registres aquí ya queda
guardado en tu clúster de Atlas (no es una base de datos local).

---

## Paso 3 — Subir el proyecto a GitHub

```bash
cd sistema_citas
git init
git add .
git commit -m "Sistema de gestión de citas médicas"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/sistema-citas-medicas.git
git push -u origin main
```

> El archivo `.gitignore` ya excluye `secrets.toml`, así que tu clave de
> MongoDB **no** se sube a GitHub. Solo se sube `secrets.toml.example`
> como plantilla vacía.

Si prefieres no usar la terminal: crea el repositorio directamente en
github.com ("New repository") y arrastra los archivos desde la interfaz
web ("Add file → Upload files").

---

## Paso 4 — Publicar en Streamlit Community Cloud (enlace público gratis)

1. Entra a **https://share.streamlit.io** e inicia sesión con tu cuenta
   de GitHub.
2. Clic en **"New app"** → elige tu repositorio, la rama `main`, y
   `app.py` como archivo principal.
3. Antes de dar clic en Deploy, abre **"Advanced settings" → Secrets** y
   pega:
   ```toml
   MONGODB_URI = "mongodb+srv://usuario:contraseña@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority"
   ADMIN_PASSWORD = "tu_clave_segura"
   ```
4. Clic en **Deploy**. En uno o dos minutos obtendrás un enlace público
   permanente, del tipo:
   ```
   https://sistema-citas-medicas.streamlit.app
   ```

Ese es el enlace que puedes compartir con tu docente o con cualquier
persona del público en general. No necesita instalar nada, y cada dato
que se registre (pacientes, citas, sanciones) queda guardado para
siempre en tu clúster de Atlas, sin importar cuántas veces Streamlit
Cloud reinicie el contenedor de la app.

---

## Notas importantes

- **Contraseña de administrador**: por defecto es `admin123` si no
  configuras `ADMIN_PASSWORD` en los secrets. Cámbiala siempre antes de
  publicar el enlace públicamente.
- **Límite gratuito de Atlas (M0)**: 512 MB de almacenamiento. Para un
  proyecto académico de gestión de citas esto equivale a decenas de
  miles de registros, más que suficiente.
- **Concurrencia**: MongoDB Atlas soporta múltiples usuarios escribiendo
  al mismo tiempo (por ejemplo, varios administradores en distintas
  ventanillas), cumpliendo con el requisito de "operación concurrente"
  mencionado en la sección 1.4 del informe.
- Si en algún momento quieres migrar de MongoDB a otra base (por
  ejemplo PostgreSQL/Supabase), solo se necesita reescribir `db.py`;
  ni `app.py` ni `priority.py` cambian, porque toda la lógica de negocio
  está separada de la capa de persistencia.

---

## Correspondencia con el informe

| Sección del informe                          | Implementación                                             |
|-----------------------------------------------|-------------------------------------------------------------|
| 2.1 Registro de pacientes                     | `db.registrar_paciente`, pestaña "Registro de pacientes"    |
| 2.1 Agendamiento y validación de horarios     | `db.crear_cita`, `db.existe_conflicto_horario`               |
| 2.1 Manejo de prioridad                       | Orden de la cola por `nivel_prioridad` en `db.listar_citas`  |
| 2.1 Búsqueda de disponibilidad                | Pestaña "Agendar cita" → horarios libres/ocupados            |
| 2.1 Cancelación / reprogramación              | Pestaña "Cancelar o reprogramar"                             |
| 1.4 Operación concurrente del personal        | MongoDB Atlas soporta múltiples escrituras simultáneas       |
| 2.2 Motor MEWS (P_total)                      | `priority.calcular_prioridad`                                |
| 2.2.1 Blacklisting y sanciones                | `db.sancionar_dni`, `db.esta_suspendido`, pestaña "Lista de suspendidos" |
