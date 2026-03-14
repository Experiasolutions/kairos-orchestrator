"""
OS Worker — Motor da Gabriel OS dentro do KAIROS SKY.
Gerencia os blocos de tempo, notificações de transição e proteção da zona 🔵.
"""
import logging
from datetime import datetime

logger = logging.getLogger("kairos.os")

# Blocos de tempo da OS v3.0
TIME_BLOCKS = [
    {"name": "AURORA", "emoji": "☀️", "start": "06:30", "end": "09:00",
     "zone": "🔴🟡", "desc": "Corpo + Mente + Alma + Casa"},
    {"name": "RAID I", "emoji": "⚔️", "start": "09:00", "end": "12:30",
     "zone": "🔵", "desc": "BLOCO DE GENIALIDADE (SAGRADO)"},
    {"name": "REABASTECIMENTO", "emoji": "🔋", "start": "12:30", "end": "13:30",
     "zone": "—", "desc": "Descanso e alimentação"},
    {"name": "RAID II", "emoji": "⚡", "start": "13:30", "end": "17:30",
     "zone": "🟢🟡", "desc": "Excelência + Impacto batched"},
    {"name": "ACADEMIA", "emoji": "📚", "start": "17:30", "end": "19:00",
     "zone": "🔵", "desc": "Estudo focado em expandir genialidade"},
    {"name": "CAMPO BASE", "emoji": "🏕️", "start": "19:00", "end": "20:30",
     "zone": "—", "desc": "Descanso e vida pessoal"},
    {"name": "SANTUÁRIO", "emoji": "🌙", "start": "20:30", "end": "22:30",
     "zone": "🔵🟢", "desc": "Revisão + Classificação Pareto amanhã"},
]


def _parse_time(t: str) -> tuple[int, int]:
    """Converte 'HH:MM' em tupla (hora, minuto)."""
    parts = t.split(":")
    return int(parts[0]), int(parts[1])


def get_current_block() -> dict | None:
    """Retorna o bloco de tempo atual baseado no horário BRT."""
    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute

    for block in TIME_BLOCKS:
        sh, sm = _parse_time(block["start"])
        eh, em = _parse_time(block["end"])
        start_min = sh * 60 + sm
        end_min = eh * 60 + em

        if start_min <= current_minutes < end_min:
            return block

    return None


def get_os_status() -> str:
    """Retorna o status atual da OS (bloco ativo, zona, próximo bloco)."""
    block = get_current_block()
    now = datetime.now()

    if not block:
        # Fora dos blocos (sono ou pré-aurora)
        if now.hour < 6 or now.hour >= 23:
            return "😴 SONO — Protegendo recuperação. Boa noite, Dragonborn."
        return "🌅 Entre blocos. Próximo: AURORA às 06:30."

    # Encontrar próximo bloco
    idx = TIME_BLOCKS.index(block)
    next_block = TIME_BLOCKS[idx + 1] if idx + 1 < len(TIME_BLOCKS) else None

    eh, em = _parse_time(block["end"])
    end_min = eh * 60 + em
    current_min = now.hour * 60 + now.minute
    remaining = end_min - current_min

    status = (
        f"{block['emoji']} BLOCO ATIVO: {block['name']} ({block['start']}–{block['end']})\n"
        f"   Zona: {block['zone']} — {block['desc']}\n"
        f"   ⏱️ Restam {remaining} minutos"
    )

    if next_block:
        status += f"\n   ➡️ Próximo: {next_block['emoji']} {next_block['name']} às {next_block['start']}"

    # Alerta de proteção da zona 🔵
    if "🔵" in block["zone"]:
        status += "\n\n   ⚠️ ZONA SAGRADA ATIVA — Apenas genialidade aqui, Dragonborn."

    return status


def check_zone_violation(task_description: str) -> str | None:
    """
    Verifica se uma tarefa sendo feita agora viola a zona do bloco atual.
    Retorna um alerta se sim, None se ok.
    """
    block = get_current_block()
    if not block or "🔵" not in block["zone"]:
        return None

    # Keywords que indicam atividade NÃO-genialidade
    non_genius_keywords = [
        "email", "mensagem", "responder", "organizar", "limpar",
        "planilha", "burocracia", "serasa", "conta", "boleto",
        "post", "social media", "instagram", "bug", "fix",
    ]

    task_lower = task_description.lower()
    for kw in non_genius_keywords:
        if kw in task_lower:
            return (
                f"⚠️ Dragonborn, estamos no {block['name']} ({block['zone']}). "
                f"Detectei que '{task_description}' parece ser 🟡 ou 🔴, não 🔵.\n"
                f"A missão de genialidade está chamando. Quer que eu anote isso pro RAID II?"
            )

    return None
