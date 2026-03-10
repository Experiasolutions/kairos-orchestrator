# Night Processor — processa check-in noturno + Pareto Score
import logging
from datetime import date
import supabase_client as db

logger = logging.getLogger("kairos.night")


def process_night_checkin(
    completed_quests: list[str],
    blocker: str = "",
    energy_tomorrow: int = 3,
    good_thing: str = "",
    genius_completed: bool = False,
    genius_minutes: int = 0,
    non_genius_in_raid: str = "",
) -> str:
    """Processa o check-in noturno e retorna o resumo."""
    logger.info("Processando Night Check-in")

    profile = db.get_profile()
    if not profile:
        return "⚠️ Perfil não encontrado."

    # Calcular Pareto Score do dia
    quests = db.get_today_quests()
    total_quests = len(quests) or 1
    completed = sum(1 for q in quests if q.get("is_completed", False))

    genius_quests = [q for q in quests if q.get("pareto_layer") == "genius"]
    excellence_quests = [q for q in quests if q.get("pareto_layer") == "excellence"]
    impact_quests = [q for q in quests if q.get("pareto_layer") == "impact"]

    genius_done = sum(1 for q in genius_quests if q.get("is_completed", False))
    excellence_done = sum(1 for q in excellence_quests if q.get("is_completed", False))
    impact_done = sum(1 for q in impact_quests if q.get("is_completed", False))

    pareto_score = {
        "genius_pct": round((genius_done / max(len(genius_quests), 1)) * 100),
        "excellence_pct": round((excellence_done / max(len(excellence_quests), 1)) * 100),
        "impact_pct": round((impact_done / max(len(impact_quests), 1)) * 100),
        "genius_minutes": genius_minutes,
        "genius_completed": genius_completed,
    }

    # XP ganho
    total_xp = sum(q.get("xp_reward", 0) for q in quests if q.get("is_completed", False))
    total_gems = sum(q.get("gem_reward", 0) for q in quests if q.get("is_completed", False))

    # Atualizar streak
    aurora_quests = [q for q in quests if q.get("block") == "aurora"]
    santuario_quests = [q for q in quests if q.get("block") == "santuario"]
    aurora_done = all(q.get("is_completed", False) for q in aurora_quests) if aurora_quests else False
    santuario_done = all(q.get("is_completed", False) for q in santuario_quests) if santuario_quests else False

    new_streak = profile.get("streak_count", 0)
    if aurora_done and santuario_done:
        new_streak += 1
    else:
        new_streak = 0

    best_streak = max(new_streak, profile.get("streak_best", 0))

    # Calcular attr_pareto (baseado em genius_minutes)
    target = profile.get("genius_zone_target", 60)
    pareto_attr = min(100, round((genius_minutes / max(target, 1)) * 100))

    # Atualizar perfil
    db.update_profile({
        "streak_count": new_streak,
        "streak_best": best_streak,
        "genius_zone_minutes": genius_minutes,
        "attr_pareto": pareto_attr,
        "attr_momentum": min(100, new_streak * 10),
        "season_day": profile.get("season_day", 1) + 1,
    })

    # Salvar no memory log
    journal = f"""NOITE — {date.today().isoformat()}
Missões: {completed}/{total_quests}
Bloqueio: {blocker or 'nenhum'}
Energia amanhã: {energy_tomorrow}/5
Coisa boa: {good_thing}
🔵 Genialidade: {'✅' if genius_completed else '❌'} ({genius_minutes}min)
Não-genialidade no RAID I: {non_genius_in_raid or 'nada'}"""

    db.log_memory(
        "night_checkin",
        journal,
        mood=energy_tomorrow,
        energy=energy_tomorrow,
        pareto=pareto_score,
    )

    # Montar resposta
    streak_text = f"🔥 STREAK: {new_streak} dias" if new_streak > 0 else "💔 Streak resetado — mas conquistas ficam."

    response = f"""🌙 RESUMO DO DIA

📊 PARETO SCORE:
  🔵 Genialidade: {pareto_score['genius_pct']}% ({genius_minutes}min)
  🟢 Excelência: {pareto_score['excellence_pct']}%
  🟡 Impacto: {pareto_score['impact_pct']}%

⚡ XP ganho: +{total_xp} XP | +{total_gems} GEMS
{streak_text}
🏆 Melhor streak: {best_streak} dias
💎 Pareto Level: {pareto_attr}%

💡 Lembra: dia ruim = dados. Não é falha — é informação.
O KAIROS nunca pune. Só registra e recalcula.

Bom descanso, Dragonborn. 🐉"""

    logger.info("Night Check-in processado: %d/%d quests, streak=%d", completed, total_quests, new_streak)
    return response
