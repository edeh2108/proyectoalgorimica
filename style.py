CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif;
}

/* ---- Fondo general ---- */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main .block-container {
    background: #dbe3e8 !important;
}

/* ---- Cabecera personalizada ---- */
.app-header {
    background: #2c5a72;
    padding: 1.4rem 2rem 1.1rem 2rem;
    margin: -1rem -1rem 1.6rem -1rem;
    border-radius: 0 0 14px 14px;
}
.app-header h1 {
    font-family: 'Sora', sans-serif;
    color: #ffffff;
    font-size: 1.65rem;
    font-weight: 700;
    margin-bottom: 0.15rem;
    letter-spacing: -0.02em;
}
.app-header p {
    color: #a9c6d4;
    font-size: 0.92rem;
    margin: 0;
}

/* ---- Tarjetas ---- */
.card {
    background: #eef2f4;
    border-radius: 14px;
    padding: 1.25rem 1.4rem;
    box-shadow: 0 2px 10px rgba(15, 40, 55, 0.06);
    border: 1px solid #c7d2d8;
    margin-bottom: 1rem;
}

/* ---- Badges de prioridad clínica ---- */
.badge {
    display: inline-block;
    padding: 0.28rem 0.75rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.82rem;
    letter-spacing: 0.01em;
}
.badge-I    { background:#fde3e3; color:#a3221f; border:1px solid #f4b8b8; }
.badge-II   { background:#fdecd6; color:#a15c05; border:1px solid #f3cf9c; }
.badge-III  { background:#fff6d6; color:#8a6d00; border:1px solid #f0e19c; }
.badge-IV   { background:#e2f3e6; color:#1f7a3b; border:1px solid #b7e1c4; }

.pill-suspendido {
    background:#fde3e3; color:#a3221f; padding: 0.6rem 0.9rem;
    border-radius: 10px; border:1px solid #f4b8b8; font-weight: 600;
}

/* ---- Botones ---- */
div.stButton > button {
    border-radius: 9px;
    font-weight: 600;
    border: none;
    padding: 0.5rem 1.1rem;
}
div.stButton > button[kind="primary"] {
    background: #2c5a72;
}
div.stButton > button[kind="primary"]:hover {
    background: #234759;
}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: #2c5a72;
}
section[data-testid="stSidebar"] * {
    color: #e7f0f4 !important;
}
section[data-testid="stSidebar"] .stRadio > label { color: #e7f0f4 !important; }

/* ---- Tablas ---- */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
}

hr { border-color: #c7d2d8; }

/* ---- Inputs / widgets (tonalidad intermedia, no blanco puro) ---- */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stDateInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stSelectbox"] div[data-baseweb="select"] div,
[data-testid="stWidgetLabel"] + div div[data-baseweb="select"] > div {
    background-color: #eef2f4 !important;
    border-color: #c7d2d8 !important;
}

/* Fallback genérico por si cambian los testids en otra versión de Streamlit */
input, textarea, select {
    background-color: #eef2f4 !important;
}

</style>
"""

HEADER_HTML = """
<div class="app-header">
    <h1>🏥 Sistema de Gestión de Citas Médicas</h1>
    <p>UNMSM · Facultad de Ingeniería de Sistemas e Informática — Algorítmica I, Grupo 7</p>
</div>
"""


def badge(nivel: str, texto: str) -> str:
    return f'<span class="badge badge-{nivel}">{texto}</span>'
