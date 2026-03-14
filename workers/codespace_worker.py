"""
Codespace Worker — Braço mecânico autônomo do KAIROS SKY.
Faz long-polling na task_queue do Supabase, executa e reporta resultado.
Roda dentro de um GitHub Codespace.
"""
import asyncio
import logging
import sys
import os

# Garantir que importamos do diretório raiz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ENVIRONMENT
from supabase_client import get_client
from workers.task_worker import process_task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("kairos.codespace-worker")

WORKER_ID = os.environ.get("CODESPACE_NAME", f"worker-{os.getpid()}")
POLL_INTERVAL = 30  # segundos entre polls


async def claim_and_execute() -> bool:
    """
    Tenta reivindicar UMA task pendente e executá-la.
    Retorna True se executou algo, False se fila vazia.
    """
    supabase = get_client()

    # Tentar pegar a task de maior prioridade que NINGUÉM pegou
    response = (
        supabase.table("task_queue")
        .select("*")
        .eq("status", "pending")
        .order("priority", desc=True)
        .limit(1)
        .execute()
    )

    tasks = response.data if hasattr(response, "data") else []
    if not tasks:
        return False

    task = tasks[0]
    task_id = task["id"]

    # Claim atômico: só executa se o status ainda for 'pending'
    claim = (
        supabase.table("task_queue")
        .update({"status": "claimed", "claimed_by": WORKER_ID})
        .eq("id", task_id)
        .eq("status", "pending")
        .execute()
    )

    if not claim.data:
        logger.info("Task %s já foi reivindicada por outro worker", task_id)
        return False

    logger.info("🔧 Task reivindicada: %s [%s]", task.get("title", "?"), WORKER_ID)

    # Executar a task
    result = process_task(task)
    logger.info("✅ Task concluída: %s → %s", task.get("title", "?"), result.get("status", "?"))
    return True


async def main() -> None:
    """Entry point do worker autônomo."""
    logger.info("═" * 50)
    logger.info("  🐉 KAIROS Codespace Worker — %s", WORKER_ID)
    logger.info("  Environment: %s", ENVIRONMENT)
    logger.info("═" * 50)

    while True:
        try:
            executed = await claim_and_execute()
            if executed:
                # Se executou, tenta pegar outra imediatamente
                continue
            else:
                logger.debug("Fila vazia. Dormindo %ds...", POLL_INTERVAL)
        except Exception as e:
            logger.error("Erro no worker loop: %s", e)

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
