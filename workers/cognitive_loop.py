"""
OODA Loop (The Cognitive Heartbeat) para o KAIROS SKY.
Substitui a passividade do cron por uma instância ativa de triagem e autoconsciência.
Integra a Gabriel OS para consciência de blocos de tempo e zonas Pareto.
"""
import asyncio
import logging
from datetime import datetime
from config import GROQ_API_KEY, GOOGLE_API_KEYS
from supabase_client import get_client
from workers.os_worker import get_current_block

logger = logging.getLogger("kairos.heartbeat")

# Cache para evitar notificações duplicadas de transição de bloco
_last_block_name: str | None = None


async def cognitive_heartbeat(bot_app, interval_seconds: int = 60):
    """
    Motor contínuo da AGI Limitada. Executa o ciclo OODA:
    - Observe: Lê filas, métricas do Supabase, bloco de tempo ativo.
    - Orient: Define o estado atual do contexto + zona Pareto.
    - Decide: Acorda sub-agentes se necessário.
    - Act: Loga as ações ou engatilha automações.
    """
    global _last_block_name
    logger.info("🧠 Cognitive Heartbeat inicializado com OODA loop (intervalo: %ds)", interval_seconds)
    supabase = get_client()

    while True:
        try:
            now = datetime.now()

            # ─── 1. OBSERVE (Percepção do Ambiente) ───────────────
            # Tasks pendentes
            response = supabase.table("task_queue").select("*").eq("status", "pending").order("priority", desc=True).limit(1).execute()
            tasks = response.data if hasattr(response, "data") else []

            # Bloco de tempo ativo (Gabriel OS)
            current_block = get_current_block()
            block_name = current_block["name"] if current_block else None

            # ─── 2. ORIENT & DECIDE (Triagem Cognitiva) ──────────

            # Detectar transição de bloco
            if block_name != _last_block_name:
                if current_block:
                    logger.info(
                        "⏰ Transição de bloco: %s → %s %s (Zona: %s)",
                        _last_block_name or "—",
                        current_block["emoji"],
                        current_block["name"],
                        current_block["zone"],
                    )
                    # Se entrando na zona 🔵 (RAID I ou ACADEMIA), alertar
                    if "🔵" in current_block["zone"]:
                        logger.info("🔵 ZONA SAGRADA ATIVA — Protegendo genialidade do Dragonborn")
                else:
                    logger.info("💤 Fora dos blocos de tempo. Modo silencioso.")
                _last_block_name = block_name

            # Tasks pendentes
            if tasks:
                impulse = f"Tarefa pendente detectada: {tasks[0].get('title', 'Unknown')}"
                logger.info("OODA [Orient]: %s", impulse)

            # ─── 3. ACT ──────────────────────────────────────────
            # Log de pulsação a cada 30 min
            if now.minute in (0, 30) and now.second < interval_seconds:
                zone_info = f" | Zona: {current_block['zone']}" if current_block else ""
                logger.info(
                    "OODA [Act]: SKY ativo em %s. %d tasks pendentes%s.",
                    now.strftime("%H:%M"),
                    len(tasks),
                    zone_info,
                )

        except Exception as e:
            logger.error("Falha no Cognitive Heartbeat: %s", e)

        # ─── 4. SLEEP (Pacing) ────────────────────────────────
        await asyncio.sleep(interval_seconds)
