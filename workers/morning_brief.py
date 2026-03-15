# Morning Brief Worker — gera briefing matinal v3.0 com Pareto + Noesis
import logging
from datetime import date
import supabase_client as db
from workers.cognitive_state import get_state_summary
from workers.learning_model import get_insights_for_brief

logger = logging.getLogger("kairos.morning")

MORNING_TEMPLATE = """☀️ BOM DIA, GABRIEL.
DIA {season_day} · {season} · STREAK: {streak} dias

💎 PARETO: Nível {level} | XP: {xp}/{xp_next}
{attr_bars}

🔵 MISSÃO DE GENIALIDADE (RAID I — SAGRADO):
{genius_quest}

🟢 MISSÕES DE EXCELÊNCIA (RAID II):
{excellence_quests}

🟡 IMPACTO (batch 30min):
{impact_quests}

⚔️ BOSSES ATIVOS:
{bosses_status}

🎯 PARETO CHECK: "Hoje, o 0.8% é a missão 🔵 acima. Todo o resto é suporte."

{cognitive_state}

{learning_insights}

Boa missão, Dragonborn. 🐉"""


def _attr_bar(name: str, value: int, emoji: str) -> str:
    """Gera barra de atributo visual."""
    filled = value // 10
    empty = 10 - filled
    bar = "█" * filled + "░" * empty
    return f"  {emoji} {name:12s} {bar} {value}%"


def _format_boss(boss: dict) -> str:
    """Formata um boss financeiro."""
    hp_pct = (float(boss["current_hp"]) / float(boss["total_hp"])) * 100 if float(boss["total_hp"]) > 0 else 0
    priority_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}.get(boss["priority"], "⚪")
    return f"  {priority_icon} {boss['name']}: R${float(boss['current_hp']):,.0f} / R${float(boss['total_hp']):,.0f} ({hp_pct:.0f}%)"


def generate_morning_brief() -> str:
    """Gera o morning brief completo."""
    logger.info("Gerando Morning Brief v2.0")

    # Dados do perfil
    profile = db.get_profile()
    if not profile:
        return "⚠️ Perfil não encontrado. Execute o schema SQL primeiro."

    # Barras de atributos
    attr_bars = "\n".join([
        _attr_bar("ENERGIA", profile.get("attr_energia", 50), "⚡"),
        _attr_bar("FOCO", profile.get("attr_foco", 50), "🧠"),
        _attr_bar("FORÇA", profile.get("attr_forca", 50), "💪"),
        _attr_bar("PROSPERIDADE", profile.get("attr_prosperidade", 0), "💰"),
        _attr_bar("CLAREZA", profile.get("attr_clareza", 50), "🌀"),
        _attr_bar("MOMENTUM", profile.get("attr_momentum", 0), "🔥"),
        _attr_bar("PARETO", profile.get("attr_pareto", 0), "💎"),
    ])

    # Missões do dia
    quests = db.get_today_quests()
    genius = [q for q in quests if q.get("pareto_layer") == "genius"]
    excellence = [q for q in quests if q.get("pareto_layer") == "excellence"]
    impact = [q for q in quests if q.get("pareto_layer") == "impact"]

    genius_text = "\n".join(f"  🔵 {q['title']}" for q in genius) or "  🔵 (definir no Santuário de ontem)"
    excellence_text = "\n".join(f"  🟢 {q['title']}" for q in excellence) or "  🟢 (nenhuma definida)"
    impact_text = "\n".join(f"  🟡 {q['title']}" for q in impact) or "  🟡 (nenhuma definida)"

    # Bosses
    bosses = db.get_bosses()
    bosses_text = "\n".join(_format_boss(b) for b in bosses[:3]) or "  Nenhum boss ativo"

    # Estado cognitivo e insights do Learning Model
    try:
        cognitive = get_state_summary()
    except Exception:
        cognitive = "🧠 Estado cognitivo indisponível"
    try:
        learning = get_insights_for_brief()
    except Exception:
        learning = "🧬 Learning Model indisponível"

    # Montar briefing
    brief = MORNING_TEMPLATE.format(
        season_day=profile.get("season_day", 1),
        season=profile.get("season", "T1-2026"),
        streak=profile.get("streak_count", 0),
        level=profile.get("level", 1),
        xp=profile.get("xp", 0),
        xp_next=profile.get("xp_next_level", 100),
        attr_bars=attr_bars,
        genius_quest=genius_text,
        excellence_quests=excellence_text,
        impact_quests=impact_text,
        bosses_status=bosses_text,
        cognitive_state=cognitive,
        learning_insights=learning,
    )

    # Salvar no memory log
    db.log_memory("morning_brief", brief)
    logger.info("Morning Brief gerado com sucesso")
    return brief
