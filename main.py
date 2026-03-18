# KAIROS SKY — Entry Point
# Orquestrador autônomo 24/7
import asyncio
import logging
import os
import sys
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import (
    MORNING_BRIEF_HOUR,
    MORNING_BRIEF_MINUTE,
    NIGHT_CHECKIN_HOUR,
    LOG_LEVEL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from tg_bot.bot import create_bot
from workers.morning_brief import generate_morning_brief
from workers.task_worker import process_pending_tasks
from workers.context_sync import get_system_status
from workers.cognitive_loop import cognitive_heartbeat
from workers.learning_model import get_model
from bridges.webhook_receiver import start_webhook_server

# ─── Logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("kairos.main")


# ─── Scheduled Jobs ─────────────────────────────────────────

async def job_morning_brief(bot_app) -> None:
    """Envia o Morning Brief automaticamente."""
    logger.info("⏰ Job: Morning Brief")
    try:
        brief = generate_morning_brief()
        if TELEGRAM_CHAT_ID and bot_app.bot:
            await bot_app.bot.send_message(
                chat_id=int(TELEGRAM_CHAT_ID),
                text=brief,
            )
            logger.info("Morning Brief enviado via Telegram")
    except Exception as e:
        logger.error("Erro no Morning Brief: %s", e)


async def job_process_tasks() -> None:
    """Processa tasks pendentes da fila."""
    logger.info("⏰ Job: Processar tasks")
    try:
        results = process_pending_tasks(limit=3)
        if results:
            completed = sum(1 for r in results if r.get("status") == "completed")
            logger.info("Tasks processadas: %d concluídas", completed)
    except Exception as e:
        logger.error("Erro ao processar tasks: %s", e)


from workers.council_auditor import convene_council


async def job_night_reminder(bot_app) -> None:
    """Lembra Gabriel do night check-in."""
    logger.info("⏰ Job: Night Check-in Reminder")
    try:
        if TELEGRAM_CHAT_ID and bot_app.bot:
            await bot_app.bot.send_message(
                chat_id=int(TELEGRAM_CHAT_ID),
                text=(
                    "🌙 HORA DO CHECK-IN, DRAGONBORN.\n\n"
                    "Use /check para iniciar ou envie direto:\n"
                    '{"blocker":"","energy":3,"good":"","genius":false,"genius_min":0}'
                ),
            )
    except Exception as e:
        logger.error("Erro no night reminder: %s", e)


async def job_council_audit() -> None:
    """Executa a auditoria diária do IA Council."""
    logger.info("⏰ Job: IA Council Audit")
    try:
        convene_council()
        logger.info("IA Council Audit finalizado.")
    except Exception as e:
        logger.error("Erro no IA Council Audit: %s", e)


async def job_keepalive() -> None:
    """Keep-alive para evitar sleep no free tier."""
    logger.debug("💓 Keep-alive ping")


# ─── Main ────────────────────────────────────────────────────

async def main() -> None:
    """Entry point principal do KAIROS SKY."""
    logger.info("═" * 50)
    logger.info("  🐉 KAIROS SKY — Iniciando...")
    logger.info("═" * 50)

    # Verificar configuração
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN não configurado!")
        sys.exit(1)

    # Criar bot
    bot_app = create_bot()

    # Configurar scheduler (BRT = UTC-3)
    scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")

    # Morning Brief — todo dia às 07:00 BRT
    scheduler.add_job(
        job_morning_brief,
        CronTrigger(hour=MORNING_BRIEF_HOUR, minute=MORNING_BRIEF_MINUTE),
        args=[bot_app],
        id="morning_brief",
        name="Morning Brief",
    )

    # Processar tasks — a cada 30 minutos
    scheduler.add_job(
        job_process_tasks,
        CronTrigger(minute="*/30"),
        id="process_tasks",
        name="Task Processor",
    )

    # Night reminder — às 22:00 BRT
    scheduler.add_job(
        job_night_reminder,
        CronTrigger(hour=NIGHT_CHECKIN_HOUR, minute=0),
        args=[bot_app],
        id="night_reminder",
        name="Night Reminder",
    )

    # IA Council Audit — às 22:30 BRT
    scheduler.add_job(
        job_council_audit,
        CronTrigger(hour=22, minute=30),
        id="council_audit",
        name="IA Council",
    )

    # Keep-alive — a cada 14 minutos
    scheduler.add_job(
        job_keepalive,
        CronTrigger(minute="*/14"),
        id="keepalive",
        name="Keep Alive",
    )

    scheduler.start()
    logger.info("Scheduler ativo com %d jobs", len(scheduler.get_jobs()))

    # Inicializar Learning Model (Anamnesis seed na primeira execução)
    try:
        model = get_model()
        logger.info(
            "🧬 Learning Model v%d carregado (%d padrões, accuracy: %.0f%%)",
            model.get("model_version", 1),
            len(model.get("inference_patterns", [])),
            float(model.get("model_accuracy", {}).get("accuracy_rate", 0)) * 100,
        )
    except Exception as e:
        logger.warning("Learning Model não carregado: %s", e)

    # Inicializar Composio Bridge
    try:
        from bridges.composio_bridge import get_status
        composio_status = get_status()
        if composio_status.get("available"):
            logger.info("🔌 Composio SDK ativo (%d apps prioritários)", composio_status.get("priority_apps_count", 0))
        else:
            logger.info("🔌 Composio SDK disponível (aguardando COMPOSIO_API_KEY)")
    except Exception as e:
        logger.warning("Composio Bridge não carregado: %s", e)

    # Verificar Squad Runner
    try:
        from workers.squad_runner import list_squads, _get_engine
        squads = list_squads()
        engine = _get_engine()
        logger.info("🐉 Squad Runner: %d squads, engine: %s", len(squads), engine)
    except Exception as e:
        logger.warning("Squad Runner não carregado: %s", e)

    # Verificar Railway Bridge (Criador de Tentáculos)
    try:
        from bridges.railway_bridge import get_status as railway_status
        rw = railway_status()
        if rw.get("available"):
            logger.info("🐙 Railway Bridge ativo: %d skills, %d patterns", rw.get("total_skills", 0), rw.get("total_patterns", 0))
        else:
            logger.info("🐙 Railway Bridge disponível (aguardando RAILWAY_API_TOKEN)")
    except Exception as e:
        logger.warning("Railway Bridge não carregado: %s", e)

    # Iniciar Webhook Receiver (Railway HTTP)
    try:
        webhook_token = os.environ.get("WEBHOOK_TOKEN", "")
        webhook_port = int(os.environ.get("PORT", "8080"))
        start_webhook_server(port=webhook_port, token=webhook_token)
        logger.info("📡 Webhook receiver ativo na porta %d", webhook_port)
    except Exception as e:
        logger.warning("Webhook receiver não iniciado: %s", e)

    # Status inicial
    try:
        status = get_system_status()
        logger.info("\n%s", status)
    except Exception as e:
        logger.warning("Não foi possível carregar status: %s", e)

    # Iniciar bot Telegram (polling)
    logger.info("🤖 Bot Telegram iniciando polling...")
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=True)

    logger.info("✅ KAIROS SKY — Operacional")

    # Manter rodando via Cognitive Heartbeat (OODA Loop) ativo
    try:
        await cognitive_heartbeat(bot_app, interval_seconds=60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Encerrando KAIROS SKY...")
        scheduler.shutdown()
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
