# KAIROS SKY — Entry Point
# Orquestrador autônomo 24/7
import asyncio
import logging
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

    # Keep-alive — a cada 14 minutos
    scheduler.add_job(
        job_keepalive,
        CronTrigger(minute="*/14"),
        id="keepalive",
        name="Keep Alive",
    )

    scheduler.start()
    logger.info("Scheduler ativo com %d jobs", len(scheduler.get_jobs()))

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

    # Manter rodando
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Encerrando KAIROS SKY...")
        scheduler.shutdown()
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
