# Cliente Supabase para KAIROS SKY
import logging
from datetime import datetime, date
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

logger = logging.getLogger("kairos.supabase")

_client: Client | None = None


def get_client() -> Client:
    """Retorna o cliente Supabase (singleton)."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_KEY são obrigatórias")
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("Supabase conectado: %s", SUPABASE_URL[:40])
    return _client


# ─── Profile ───────────────────────────────────────────────

def get_profile() -> dict:
    """Retorna o perfil do operador."""
    resp = get_client().table("profile").select("*").limit(1).execute()
    if resp.data:
        return resp.data[0]
    return {}


def update_profile(updates: dict) -> dict:
    """Atualiza campos do perfil."""
    profile = get_profile()
    if not profile:
        return {}
    resp = get_client().table("profile").update(updates).eq("id", profile["id"]).execute()
    return resp.data[0] if resp.data else {}


def add_xp(amount: int) -> dict:
    """Adiciona XP e sobe de nível se necessário."""
    profile = get_profile()
    if not profile:
        return {}
    new_xp = profile["xp"] + amount
    new_level = profile["level"]
    xp_next = profile["xp_next_level"]
    while new_xp >= xp_next:
        new_xp -= xp_next
        new_level += 1
        xp_next = int(xp_next * 1.5)
    return update_profile({
        "xp": new_xp,
        "level": new_level,
        "xp_next_level": xp_next,
    })


# ─── Quests ────────────────────────────────────────────────

def get_today_quests() -> list[dict]:
    """Retorna missões de hoje."""
    today = date.today().isoformat()
    resp = get_client().table("quests_daily").select("*").eq("quest_date", today).order("created_at").execute()
    return resp.data or []


def complete_quest(quest_id: str) -> dict:
    """Marca missão como concluída e dá XP."""
    resp = get_client().table("quests_daily").update({
        "is_completed": True,
        "completed_at": datetime.now().isoformat(),
    }).eq("id", quest_id).execute()
    if resp.data:
        quest = resp.data[0]
        add_xp(quest.get("xp_reward", 0))
        return quest
    return {}


def create_daily_quests(quests: list[dict]) -> list[dict]:
    """Cria missões do dia."""
    today = date.today().isoformat()
    for q in quests:
        q["quest_date"] = today
    resp = get_client().table("quests_daily").insert(quests).execute()
    return resp.data or []


# ─── Bosses ────────────────────────────────────────────────

def get_bosses() -> list[dict]:
    """Retorna todos os bosses financeiros ativos."""
    resp = get_client().table("bosses_finance").select("*").neq("status", "defeated").order("priority").execute()
    return resp.data or []


def damage_boss(boss_id: str, amount: float) -> dict:
    """Reduz HP de um boss (pagamento de dívida)."""
    resp = get_client().table("bosses_finance").select("*").eq("id", boss_id).execute()
    if not resp.data:
        return {}
    boss = resp.data[0]
    new_hp = max(0, float(boss["current_hp"]) - amount)
    status = "defeated" if new_hp <= 0 else boss["status"]
    return get_client().table("bosses_finance").update({
        "current_hp": new_hp,
        "status": status,
    }).eq("id", boss_id).execute().data[0]


# ─── Task Queue ────────────────────────────────────────────

def get_pending_tasks(limit: int = 5) -> list[dict]:
    """Retorna tasks pendentes ordenadas por prioridade."""
    resp = get_client().table("task_queue").select("*").eq("status", "pending").order("priority", desc=True).limit(limit).execute()
    return resp.data or []


def update_task_status(task_id: str, status: str, output: dict | None = None, error: str | None = None) -> dict:
    """Atualiza status de uma task."""
    updates: dict = {"status": status}
    if status in ("completed", "failed"):
        updates["processed_at"] = datetime.now().isoformat()
    if output is not None:
        updates["output_data"] = output
    if error is not None:
        updates["error_message"] = error
    resp = get_client().table("task_queue").update(updates).eq("id", task_id).execute()
    return resp.data[0] if resp.data else {}


def add_task(title: str, category: str = "general", priority: int = 5, input_data: dict | None = None, created_by: str = "system") -> dict:
    """Adiciona uma task à fila."""
    resp = get_client().table("task_queue").insert({
        "title": title,
        "category": category,
        "priority": priority,
        "input_data": input_data or {},
        "created_by": created_by,
    }).execute()
    return resp.data[0] if resp.data else {}


# ─── Context Store ─────────────────────────────────────────

def get_context(key: str) -> dict | None:
    """Lê um valor do context store."""
    resp = get_client().table("context_store").select("*").eq("key", key).execute()
    if resp.data:
        return resp.data[0].get("value")
    return None


def set_context(key: str, value: dict, updated_by: str = "orchestrator") -> dict:
    """Atualiza um valor no context store (upsert)."""
    resp = get_client().table("context_store").upsert({
        "key": key,
        "value": value,
        "updated_by": updated_by,
    }, on_conflict="key").execute()
    return resp.data[0] if resp.data else {}


# ─── Memory Log ────────────────────────────────────────────

def log_memory(log_type: str, content: str, metadata: dict | None = None, mood: int | None = None, energy: int | None = None, pareto: dict | None = None) -> dict:
    """Registra uma entrada no log de memória."""
    entry: dict = {
        "log_type": log_type,
        "content": content,
        "log_date": date.today().isoformat(),
    }
    if metadata:
        entry["metadata"] = metadata
    if mood:
        entry["mood_score"] = mood
    if energy:
        entry["energy_score"] = energy
    if pareto:
        entry["pareto_score"] = pareto
    resp = get_client().table("memory_log").insert(entry).execute()
    return resp.data[0] if resp.data else {}


# ─── Leads ─────────────────────────────────────────────────

def get_leads(status: str | None = None) -> list[dict]:
    """Retorna leads, opcionalmente filtrados por status."""
    query = get_client().table("leads").select("*").order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    return query.execute().data or []


# ─── Loot Shop ─────────────────────────────────────────────

def get_loot_items(unlocked_only: bool = False) -> list[dict]:
    """Retorna itens da loot shop."""
    query = get_client().table("loot_shop").select("*").order("tier")
    if unlocked_only:
        query = query.eq("is_unlocked", True)
    return query.execute().data or []


# ─── Knowledge Brain ───────────────────────────────────────

def search_knowledge(query: str, category: str | None = None, limit: int = 5) -> list[dict]:
    """Busca no Knowledge Brain usando full-text search."""
    try:
        params: dict = {"search_query": query, "match_limit": limit}
        if category:
            params["match_category"] = category
        resp = get_client().rpc("search_knowledge", params).execute()
        return resp.data or []
    except Exception as e:
        logger.warning("Knowledge Brain search falhou: %s", e)
        # Fallback: busca simples via ILIKE
        try:
            resp = get_client().table("knowledge_brain").select(
                "file_path,file_name,category,summary,content_chunk,tags"
            ).ilike("summary", f"%{query}%").limit(limit).execute()
            return resp.data or []
        except Exception:
            return []


def get_brain_context(query: str, max_chunks: int = 3) -> str:
    """Retorna contexto do Knowledge Brain formatado para injeção em prompts."""
    results = search_knowledge(query, limit=max_chunks)
    if not results:
        return ""

    context_parts = ["--- KNOWLEDGE BRAIN CONTEXT ---"]
    for r in results:
        source = r.get("file_name", "unknown")
        summary = r.get("summary", "")
        chunk = r.get("content_chunk", "")
        context_parts.append(f"\n[Fonte: {source}]\n{summary}\n{chunk[:2000]}")

    context_parts.append("--- END CONTEXT ---\n")
    return "\n".join(context_parts)
