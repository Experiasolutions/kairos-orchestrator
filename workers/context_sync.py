# Context Sync Worker — sincroniza Opus ↔ Orquestrador
import logging
import supabase_client as db

logger = logging.getLogger("kairos.sync")


def sync_from_opus(payload: dict) -> str:
    """Processa atualização vinda de uma sessão Opus/Antigravity.

    Payload esperado:
    {
        "decisions": ["decisão 1", "decisão 2"],
        "directives": ["diretriz para orquestrador"],
        "context_updates": {"chave": "valor"},
        "next_tasks": [{"title": "...", "category": "...", "priority": 5}]
    }
    """
    logger.info("Sincronizando dados do Opus")

    # 1. Salvar decisões no memory log
    decisions = payload.get("decisions", [])
    for decision in decisions:
        db.log_memory("decision", decision, metadata={"source": "opus"})

    # 2. Atualizar context store
    context_updates = payload.get("context_updates", {})
    for key, value in context_updates.items():
        db.set_context(key, value, updated_by="opus")

    # 3. Salvar sessão inteira no context store
    db.set_context("last_session", payload, updated_by="opus")

    # 4. Adicionar tasks à fila
    tasks = payload.get("next_tasks", [])
    for task in tasks:
        db.add_task(
            title=task.get("title", "Task sem título"),
            category=task.get("category", "general"),
            priority=task.get("priority", 5),
            created_by="opus",
        )

    # 5. Salvar directives
    directives = payload.get("directives", [])
    if directives:
        db.set_context("active_directives", {"directives": directives}, updated_by="opus")

    summary = (
        f"✅ Sync Opus concluído:\n"
        f"  → {len(decisions)} decisões registradas\n"
        f"  → {len(context_updates)} contextos atualizados\n"
        f"  → {len(tasks)} tasks adicionadas\n"
        f"  → {len(directives)} diretivas ativas"
    )
    logger.info(summary)
    return summary


def get_system_status() -> str:
    """Retorna status atual do sistema para contextualização."""
    profile = db.get_profile()
    bosses = db.get_bosses()
    pending = db.get_pending_tasks()
    leads = db.get_leads()

    total_debt = sum(float(b.get("current_hp", 0)) for b in bosses)
    active_leads = sum(1 for l in leads if l.get("status") not in ("closed_won", "closed_lost"))

    return f"""📊 STATUS KAIROS SKY
NV.{profile.get('level', 1)} | XP: {profile.get('xp', 0)} | Streak: {profile.get('streak_count', 0)}
Season: {profile.get('season', '?')} Dia {profile.get('season_day', 1)}/90
Tasks pendentes: {len(pending)}
Leads ativos: {active_leads}
Dívida total: R${total_debt:,.0f}
Pareto: {profile.get('attr_pareto', 0)}%"""
