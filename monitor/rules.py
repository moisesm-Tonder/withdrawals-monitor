import re

from monitor.types import ErrorRule

ERROR_PREFIX = re.compile(
    r"Failed to create disbursement: Failed to create disbursement:",
    re.IGNORECASE,
)

RULES: list[ErrorRule] = [
    ErrorRule(
        error_type="fecha_operacion",
        regex=re.compile(r"La fecha de operacion no debe ser menor", re.IGNORECASE),
        severity="HIGH",
        min_count=3,
    ),
    ErrorRule(
        error_type="stp_server_error",
        regex=re.compile(r"500 Server Error|500 Internal", re.IGNORECASE),
        severity="CRITICAL",
        min_count=2,
    ),
    ErrorRule(
        error_type="firma_invalida",
        regex=re.compile(r"Error validando la firma|firma invalida", re.IGNORECASE),
        severity="HIGH",
        min_count=3,
    ),
    ErrorRule(
        error_type="clabe_invalida",
        regex=re.compile(r"CLABE|digito verificador", re.IGNORECASE),
        severity="HIGH",
        min_count=3,
    ),
    ErrorRule(
        error_type="institucion_invalida",
        regex=re.compile(r"La Institucion .* no es|institucion .* no es", re.IGNORECASE),
        severity="HIGH",
        min_count=3,
    ),
    ErrorRule(
        error_type="orden_duplicada",
        regex=re.compile(
            r"orden con cl[aá]ve.*ya existe|clave de rastreo.*ya existe|duplicad",
            re.IGNORECASE,
        ),
        severity="INFO",
        min_count=5,
    ),
    ErrorRule(
        error_type="other_disbursement_error",
        regex=None,
        severity="HIGH",
        min_count=3,
    ),
]

RCA_HINTS = {
    "fecha_operacion": {
        "cause": "La fecha enviada al STP parece invalida o fuera de ventana.",
        "impact": "Retiros rechazados por validacion de negocio.",
        "action": "Revisar mapeo/formato de fecha y timezone antes de enviar a STP.",
    },
    "stp_server_error": {
        "cause": "Falla de disponibilidad o error interno de STP.",
        "impact": "Retiros no procesados temporalmente para multiples clientes.",
        "action": "Validar estado de STP, timeouts/retries y monitorear recuperacion.",
    },
    "firma_invalida": {
        "cause": "La firma criptografica enviada a STP no pasa validacion.",
        "impact": "Retiros rechazados de forma recurrente hasta corregir firma/certificado.",
        "action": "Verificar llaves/certificados, algoritmo de firma y payload firmado.",
    },
    "clabe_invalida": {
        "cause": "CLABE o digito verificador invalido en datos del beneficiario.",
        "impact": "Retiros fallidos para cuentas con datos bancarios incorrectos.",
        "action": "Validar CLABE en origen y bloquear solicitudes con formato invalido.",
    },
    "institucion_invalida": {
        "cause": "Codigo de institucion contraparte no reconocido por STP.",
        "impact": "Retiros rechazados para instituciones mal configuradas.",
        "action": "Corregir catalogo de instituciones y validarlo antes de enviar.",
    },
    "orden_duplicada": {
        "cause": "Reenvio de una orden/clave de rastreo ya procesada por STP.",
        "impact": "Duplicidad rechazada; posible reintento incorrecto del flujo.",
        "action": "Asegurar idempotencia y generar claves de rastreo unicas por intento.",
    },
    "other_disbursement_error": {
        "cause": "Error no clasificado durante la creacion de disbursement.",
        "impact": "Retiros pueden fallar de forma recurrente.",
        "action": "Inspeccionar payloads fallidos y logs de integracion.",
    },
}
