from anthropic import Anthropic

from monitor.rules import RCA_HINTS


def generate_analysis_with_claude(
    client: Anthropic,
    error_type: str,
    severity: str,
    occurrences: int,
    sample_message: str,
) -> str:
    prompt = (
        "Eres un analista SRE. Devuelve respuesta breve en espanol y con 3 lineas:\n"
        "1) Causa probable:\n"
        "2) Impacto potencial:\n"
        "3) Accion sugerida:\n\n"
        f"Error type: {error_type}\n"
        f"Severity: {severity}\n"
        f"Ocurrencias: {occurrences}\n"
        f"Ejemplo de error: {sample_message[:500]}\n"
    )
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=180,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def generate_fallback_analysis(error_type: str, occurrences: int) -> str:
    hint = RCA_HINTS[error_type]
    return (
        f"Causa probable: {hint['cause']}\n"
        f"Impacto potencial: {hint['impact']} (ocurrencias: {occurrences}).\n"
        f"Accion sugerida: {hint['action']}"
    )
