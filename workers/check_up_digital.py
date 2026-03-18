# KAIROS SKY — Check-up Digital Worker
# Gera uma auditoria digital rápida de um negócio/lead
# Usado pelo pipeline de vendas: lead entra → check-up → follow-up
import logging
from datetime import datetime, timezone

logger = logging.getLogger("kairos.checkup_digital")


def generate_checkup(
    business_name: str,
    niche: str = "",
    city: str = "",
) -> dict[str, object]:
    """
    Gera um check-up digital de um negócio.

    Args:
        business_name: Nome do negócio/empresa
        niche: Nicho de atuação (ex: "clínica veterinária")
        city: Cidade/região

    Returns:
        Relatório do check-up com score e recomendações
    """
    logger.info(
        "🔍 Check-up digital: %s (%s, %s)", business_name, niche, city,
    )

    prompt = (
        f"Faça um check-up digital rápido do negócio '{business_name}'"
        f"{' no nicho ' + niche if niche else ''}"
        f"{' em ' + city if city else ''}.\n\n"
        "Analise os seguintes pontos e dê uma nota de 0-10 para cada:\n"
        "1. **Presença no Google** (Google Meu Negócio, avaliações)\n"
        "2. **Website** (existe? é responsivo? tem CTA?)\n"
        "3. **Redes Sociais** (frequência, engajamento, profissionalismo)\n"
        "4. **WhatsApp Business** (atendimento rápido, catálogo)\n"
        "5. **Reputação Online** (Reclame Aqui, reviews negativos)\n\n"
        "Finalize com:\n"
        "- **Score Geral** (média das notas)\n"
        "- **Top 3 Quick Wins** (ações que podem gerar resultado em 7 dias)\n"
        "- **Proposta de Valor** (1 frase do que a Experia faria por este negócio)\n\n"
        "Formato: relatório direto, sem enrolação. Máximo 300 palavras."
    )

    try:
        from workers.task_worker import call_gemini
        result = call_gemini(prompt, task_type="research")
        return {
            "business_name": business_name,
            "niche": niche,
            "city": city,
            "status": "completed",
            "report": result,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("Erro no check-up digital: %s", e)
        return {
            "business_name": business_name,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }


def format_checkup_telegram(checkup_result: dict[str, object]) -> str:
    """Formata o resultado do check-up para envio no Telegram."""
    if checkup_result.get("status") == "failed":
        return f"❌ Erro no check-up: {checkup_result.get('error', 'desconhecido')}"

    business = checkup_result.get("business_name", "?")
    report = checkup_result.get("report", "Sem dados")

    header = (
        f"🔍 CHECK-UP DIGITAL\n"
        f"📌 {business}\n"
        f"{'─' * 30}\n\n"
    )

    return header + str(report)
