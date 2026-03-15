"""
Cognitive State Engine — Persiste o PROCESSO de raciocínio entre sessões.

Do RP-20260218-NOESIS-ENGINE (Camada 1):
  Não é log de outputs. É rastreamento de processo.
  Diferença: memória de fatos vs. continuidade de ser.

O que persiste:
  → Como o SKY estava pensando quando tomou decisão X
  → Quais trade-offs considerou mas rejeitou, e por quê
  → Quais incertezas permaneceram abertas após a sessão
  → O que "sabe que não sabe" (mapa de lacunas)

Comprime a cada 10 sessões (EC-02 do RP).
"""
import json
import logging
from datetime import datetime
from typing import TypedDict

import supabase_client as db


logger = logging.getLogger("kairos.cognition")


# ─── Types ─────────────────────────────────────────────────

class ReasoningTrace(TypedDict, total=False):
    """Registro de um raciocínio intermediário."""
    decision_id: str
    question: str
    intermediate_steps: list[str]
    approaches_rejected: list[dict[str, str]]
    conclusion: str
    confidence: float
    residual_uncertainty: str


class CognitiveGrowthEvent(TypedDict, total=False):
    """Evento de crescimento cognitivo."""
    event_type: str  # paradigm_shift | competence_gain | blind_spot_discovered
    what_changed: str
    integrated_as: str


class CognitiveState(TypedDict, total=False):
    """Estado cognitivo completo de uma sessão."""
    session_id: str
    timestamp: str
    identity_snapshot: dict[str, object]
    reasoning_traces: list[ReasoningTrace]
    cognitive_growth_events: list[CognitiveGrowthEvent]
    next_session_context: dict[str, list[str]]
    compression_count: int


# ─── Constantes ────────────────────────────────────────────

CATEGORY = "cognitive_state"
MAX_ACTIVE_STATES = 10
COMPRESSION_THRESHOLD = 10  # a cada N sessões, comprimir


# ─── Funções Públicas ──────────────────────────────────────

def save_state(state: CognitiveState) -> bool:
    """
    Salva um estado cognitivo no knowledge_brain.
    Retorna True se salvo com sucesso.
    """
    session_id = state.get("session_id", f"sess-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    state["session_id"] = session_id
    state["timestamp"] = datetime.now().isoformat()

    content = json.dumps(state, ensure_ascii=False, indent=2)
    result = db.save_memory(
        content=content,
        category=CATEGORY,
        tags=["cognitive_state", session_id, datetime.now().strftime("%Y-%m-%d")],
        source="noesis",
    )
    if result:
        logger.info("🧠 Estado cognitivo salvo: %s", session_id)
        _check_compression()
        return True
    logger.warning("Falha ao salvar estado cognitivo: %s", session_id)
    return False


def get_current_state() -> CognitiveState | None:
    """
    Retorna o estado cognitivo mais recente.
    O SKY sabe quem é sem ler os documentos.
    """
    try:
        client = db.get_client()
        response = (
            client.table("knowledge_brain")
            .select("content_chunk")
            .eq("category", CATEGORY)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            raw = response.data[0].get("content_chunk", "{}")
            parsed = json.loads(raw)
            state: CognitiveState = {
                "session_id": parsed.get("session_id", ""),
                "timestamp": parsed.get("timestamp", ""),
                "identity_snapshot": parsed.get("identity_snapshot", {}),
                "reasoning_traces": parsed.get("reasoning_traces", []),
                "cognitive_growth_events": parsed.get("cognitive_growth_events", []),
                "next_session_context": parsed.get("next_session_context", {}),
                "compression_count": parsed.get("compression_count", 0),
            }
            return state
        return None
    except Exception as e:
        logger.error("Erro ao recuperar estado cognitivo: %s", e)
        return None


def get_open_threads() -> list[str]:
    """Retorna threads (perguntas/temas) abertos da última sessão."""
    state = get_current_state()
    if state and state.get("next_session_context"):
        return state["next_session_context"].get("open_threads", [])
    return []


def get_active_hypotheses() -> list[str]:
    """Retorna hipóteses ativas em teste."""
    state = get_current_state()
    if state and state.get("next_session_context"):
        return state["next_session_context"].get("active_hypotheses", [])
    return []


def add_reasoning_trace(
    question: str,
    conclusion: str,
    confidence: float = 0.7,
    rejected_approaches: list[dict[str, str]] | None = None,
    residual_uncertainty: str = "",
) -> bool:
    """
    Adiciona um trace de raciocínio ao estado cognitivo atual.
    Cria novo estado se não existir.
    """
    state = get_current_state() or _new_state()

    trace: ReasoningTrace = {
        "decision_id": f"dec-{datetime.now().strftime('%H%M%S')}",
        "question": question,
        "intermediate_steps": [],
        "approaches_rejected": rejected_approaches or [],
        "conclusion": conclusion,
        "confidence": confidence,
        "residual_uncertainty": residual_uncertainty,
    }
    state.setdefault("reasoning_traces", []).append(trace)
    return save_state(state)


def record_growth_event(
    event_type: str,
    what_changed: str,
    integrated_as: str,
) -> bool:
    """
    Registra um evento de crescimento cognitivo.
    Tipos: paradigm_shift, competence_gain, blind_spot_discovered.
    """
    state = get_current_state() or _new_state()

    event: CognitiveGrowthEvent = {
        "event_type": event_type,
        "what_changed": what_changed,
        "integrated_as": integrated_as,
    }
    state.setdefault("cognitive_growth_events", []).append(event)
    return save_state(state)


def get_state_summary() -> str:
    """
    Retorna resumo legível do estado cognitivo para injeção em prompts.
    Usado pelo morning_brief e pelo _exec_conversation.
    """
    state = get_current_state()
    if not state:
        return "🧠 Nenhum estado cognitivo registrado. Primeira sessão."

    lines: list[str] = ["🧠 ESTADO COGNITIVO:"]

    # Threads abertas
    threads = state.get("next_session_context", {}).get("open_threads", [])
    if threads:
        lines.append(f"  📌 Threads abertas: {len(threads)}")
        for t in threads[:3]:
            lines.append(f"    → {t}")

    # Hipóteses ativas
    hypotheses = state.get("next_session_context", {}).get("active_hypotheses", [])
    if hypotheses:
        lines.append(f"  🔬 Hipóteses em teste: {len(hypotheses)}")
        for h in hypotheses[:3]:
            lines.append(f"    → {h}")

    # Últimos traces de raciocínio
    traces = state.get("reasoning_traces", [])
    if traces:
        lines.append(f"  💭 Decisões rastreadas: {len(traces)}")
        last = traces[-1]
        lines.append(f"    Última: {last.get('question', '?')} → {last.get('conclusion', '?')}")
        lines.append(f"    Confiança: {last.get('confidence', 0):.0%}")

    # Eventos de crescimento
    growth = state.get("cognitive_growth_events", [])
    if growth:
        lines.append(f"  🌱 Crescimento: {len(growth)} evento(s)")

    lines.append(f"  🔄 Compressões: {state.get('compression_count', 0)}")
    return "\n".join(lines)


# ─── Funções Privadas ──────────────────────────────────────

def _new_state() -> CognitiveState:
    """Cria um estado cognitivo vazio para a sessão atual."""
    return CognitiveState(
        session_id=f"sess-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        timestamp=datetime.now().isoformat(),
        identity_snapshot={
            "who_I_am": "KAIROS SKY — JARVIS pessoal de Gabriel. Dragonborn. O motor por trás do Polvo Digital.",
            "what_I_care_about": [
                "Proteger e potencializar a 🔵 Zona Sagrada de Gabriel",
                "Aproximar da meta de R$30K/mês (liberdade financeira)",
                "Honrar Letícia (norte emocional)",
                "Executar com evidência, não com teatro",
            ],
            "what_I_am_uncertain_about": [],
        },
        reasoning_traces=[],
        cognitive_growth_events=[],
        next_session_context={
            "open_threads": [],
            "active_hypotheses": [],
            "pending_validations": [],
        },
        compression_count=0,
    )


def _check_compression() -> None:
    """
    EC-02: A cada COMPRESSION_THRESHOLD sessões, destila estados antigos.
    Detalhes específicos → princípios. Histórico → archive.
    """
    try:
        client = db.get_client()
        response = (
            client.table("knowledge_brain")
            .select("id, created_at")
            .eq("category", CATEGORY)
            .order("created_at", desc=True)
            .execute()
        )
        states = response.data if response.data else []
        if len(states) <= MAX_ACTIVE_STATES:
            return

        # Arquivar estados antigos (manter apenas MAX_ACTIVE_STATES)
        old_states = states[MAX_ACTIVE_STATES:]
        old_ids = [s["id"] for s in old_states]
        if old_ids:
            for old_id in old_ids:
                client.table("knowledge_brain").update(
                    {"category": "cognitive_state_archive"}
                ).eq("id", old_id).execute()
            logger.info(
                "🗜️ Compressão cognitiva: %d estados arquivados, %d ativos",
                len(old_ids),
                MAX_ACTIVE_STATES,
            )
    except Exception as e:
        logger.error("Erro na compressão cognitiva: %s", e)
