"""
Motor algorítmico de priorización clínica.
Implementa la fórmula del informe:

    P_total = E + sum(S_i * W_i)

Donde:
    E  -> factor de riesgo por edad/condición (gestante o >60 años = 2 pts)
    S_i -> severidad de cada síntoma (0..3, según escala cerrada)
    W_i -> peso clínico del síntoma (en este modelo cada síntoma ya viene
           ponderado dentro de su propia escala, por lo que W_i = 1 para
           todas las variables, tal como se describe en el cuestionario
           de triaje del documento).

Niveles de estratificación:
    Prioridad I   (Emergencia Roja)   -> total >= 6   -> posición 0 en la cola
    Prioridad II  (Urgencia Mayor)    -> 4 <= total <= 5 -> inserción prioritaria
    Prioridad III (Urgencia Menor)    -> 1 <= total <= 3 -> turno más cercano del día
    Prioridad IV  (Cita de Rutina)    -> total == 0     -> asignación secuencial estándar
"""

from dataclasses import dataclass

# Escalas cerradas de triaje (severidad S_i)
ESCALA_RESPIRATORIA = {
    "Normal": 0,
    "Moderada o con sibilancias": 2,
    "Severa, con cianosis o ahogo en reposo": 3,
}

ESCALA_CONCIENCIA = {
    "Alerta y orientado": 0,
    "Confuso o desorientado": 2,
    "Letárgico o sin respuesta": 3,
}

ESCALA_TEMPERATURA = {
    "Rango normal (36°C - 38°C)": 0,
    "Fiebre moderada (>38°C)": 1,
    "Fiebre alta (>39°C) o Hipotermia (<35°C)": 2,
}

ESCALA_DOLOR = {
    "Leve (1-3)": 0,
    "Moderado (4-7)": 1,
    "Severo (8-10)": 2,
}

PESO_EDAD_CONDICION = 2  # E: >60 años o gestante


@dataclass
class ResultadoTriaje:
    puntaje_total: int
    nivel: str          
    etiqueta: str        
    posicion_cola: str   
    tiempo_sugerido: str


def calcular_prioridad(
    dificultad_respiratoria: str,
    estado_conciencia: str,
    temperatura: str,
    dolor: str,
    edad: int,
    gestante: bool = False,
) -> ResultadoTriaje:
    """Calcula P_total y determina el nivel de prioridad clínica."""

    E = PESO_EDAD_CONDICION if (edad > 60 or gestante) else 0

    s_resp = ESCALA_RESPIRATORIA.get(dificultad_respiratoria, 0)
    s_conc = ESCALA_CONCIENCIA.get(estado_conciencia, 0)
    s_temp = ESCALA_TEMPERATURA.get(temperatura, 0)
    s_dolor = ESCALA_DOLOR.get(dolor, 0)

    total = E + s_resp + s_conc + s_temp + s_dolor

    if total >= 6:
        nivel, etiqueta = "I", "Prioridad I - Emergencia Roja"
        posicion, tiempo = "Posición 0 (inicio inmediato de la cola)", "Atención inmediata"
    elif 4 <= total <= 5:
        nivel, etiqueta = "II", "Prioridad II - Urgencia Mayor"
        posicion, tiempo = "Inserción prioritaria", "Sugerida en menos de 15 minutos"
    elif 1 <= total <= 3:
        nivel, etiqueta = "III", "Prioridad III - Urgencia Menor"
        posicion, tiempo = "Turno más cercano disponible del día", "El mismo día"
    else:
        nivel, etiqueta = "IV", "Prioridad IV - Cita de Rutina"
        posicion, tiempo = "Asignación secuencial estándar", "Según disponibilidad de agenda"

    return ResultadoTriaje(
        puntaje_total=total,
        nivel=nivel,
        etiqueta=etiqueta,
        posicion_cola=posicion,
        tiempo_sugerido=tiempo,
    )


# Orden de prioridad para ordenar colas (menor número = más urgente)
ORDEN_NIVEL = {"I": 0, "II": 1, "III": 2, "IV": 3}
