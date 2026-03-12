# Telegram Bot — handlers para comandos do Gabriel
import logging
import json
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from workers.morning_brief import generate_morning_brief
from workers.night_processor import process_night_checkin
from workers.context_sync import sync_from_opus, get_system_status
from workers.task_worker import process_pending_tasks, call_model
import supabase_client as db

logger = logging.getLogger("kairos.telegram")


def _is_authorized(update: Update) -> bool:
    """Verifica se o usuário é o Gabriel."""
    chat_id = str(update.effective_chat.id) if update.effective_chat else ""
    if TELEGRAM_CHAT_ID and chat_id != TELEGRAM_CHAT_ID:
        logger.warning("Acesso não autorizado: chat_id=%s", chat_id)
        return False
    return True


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /start — boas-vindas."""
    if not _is_authorized(update):
        return
    chat_id = update.effective_chat.id if update.effective_chat else "unknown"
    msg = (
        "🐉 KAIROS SKY — Online\n\n"
        f"Chat ID: `{chat_id}`\n\n"
        "Comandos:\n"
        "/brief — Morning Brief\n"
        "/status — Status do sistema\n"
        "/quests — Missões de hoje\n"
        "/bosses — Bosses financeiros\n"
        "/check — Night Check-in\n"
        "/task [descrição] — Adicionar task\n"
        "/process — Processar tasks pendentes\n"
        "/sync — Sincronizar com Opus\n"
        "/ask [pergunta] — Perguntar à IA\n"
    )
    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gera e envia o Morning Brief."""
    if not _is_authorized(update):
        return
    if update.message:
        await update.message.reply_text("⏳ Gerando briefing...")
        brief = generate_morning_brief()
        # Telegram tem limite de 4096 chars
        if len(brief) > 4000:
            for i in range(0, len(brief), 4000):
                await update.message.reply_text(brief[i:i+4000])
        else:
            await update.message.reply_text(brief)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retorna status do sistema."""
    if not _is_authorized(update):
        return
    if update.message:
        status = get_system_status()
        await update.message.reply_text(status)


async def cmd_quests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista missões de hoje."""
    if not _is_authorized(update):
        return
    if not update.message:
        return
    quests = db.get_today_quests()
    if not quests:
        await update.message.reply_text("📋 Nenhuma missão definida para hoje.\nUse /task para adicionar.")
        return

    layers = {"genius": "🔵", "excellence": "🟢", "impact": "🟡", "vortex": "🔴"}
    lines = ["📋 MISSÕES DE HOJE\n"]
    for q in quests:
        icon = layers.get(q.get("pareto_layer", "impact"), "⚪")
        check = "✅" if q.get("is_completed") else "⬜"
        lines.append(f"{check} {icon} {q['title']}")

    completed = sum(1 for q in quests if q.get("is_completed"))
    lines.append(f"\nProgresso: {completed}/{len(quests)}")
    await update.message.reply_text("\n".join(lines))


async def cmd_bosses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista bosses financeiros."""
    if not _is_authorized(update):
        return
    if not update.message:
        return

    bosses = db.get_bosses()
    if not bosses:
        await update.message.reply_text("🎉 Todos os bosses derrotados!")
        return

    priority_icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}
    lines = ["⚔️ BOSSES FINANCEIROS\n"]
    total = 0.0
    for b in bosses:
        icon = priority_icons.get(b.get("priority", "medium"), "⚪")
        hp = float(b.get("current_hp", 0))
        total_hp = float(b.get("total_hp", 1))
        pct = (hp / total_hp * 100) if total_hp > 0 else 0
        filled = int(pct / 10)
        bar = "█" * filled + "░" * (10 - filled)
        lines.append(f"{icon} {b['name']}")
        lines.append(f"   {bar} R${hp:,.0f} ({pct:.0f}%)")
        total += hp

    lines.append(f"\n💀 Total: R${total:,.0f}")
    await update.message.reply_text("\n".join(lines))


async def cmd_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adiciona task à fila."""
    if not _is_authorized(update):
        return
    if not update.message or not context.args:
        if update.message:
            await update.message.reply_text("Uso: /task [descrição da task]")
        return

    title = " ".join(context.args)
    task = db.add_task(title, created_by="gabriel")
    await update.message.reply_text(f"✅ Task adicionada: {title}")


async def cmd_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa tasks pendentes."""
    if not _is_authorized(update):
        return
    if not update.message:
        return

    await update.message.reply_text("⏳ Processando tasks pendentes...")
    results = process_pending_tasks()
    if not results:
        await update.message.reply_text("📋 Nenhuma task pendente.")
        return

    completed = sum(1 for r in results if r.get("status") == "completed")
    failed = sum(1 for r in results if r.get("status") == "failed")
    await update.message.reply_text(f"✅ {completed} concluídas | ❌ {failed} falharam")


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia night check-in."""
    if not _is_authorized(update):
        return
    if not update.message:
        return

    msg = (
        "🌙 NIGHT CHECK-IN\n\n"
        "Responda com um JSON ou texto:\n"
        "1. Missões concluídas (lista)\n"
        "2. O que bloqueou (1 palavra)\n"
        "3. Energia amanhã (1-5)\n"
        "4. 1 coisa boa do dia\n"
        "5. Missão 🔵 concluída? (sim/não)\n"
        "6. Minutos na zona 🔵\n\n"
        "Exemplo:\n"
        '{"blocker":"cansaço","energy":3,"good":"terminei o OS","genius":true,"genius_min":45}'
    )
    await update.message.reply_text(msg)


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pergunta direta à IA."""
    if not _is_authorized(update):
        return
    if not update.message or not context.args:
        if update.message:
            await update.message.reply_text("Uso: /ask [sua pergunta]")
        return

    question = " ".join(context.args)
    await update.message.reply_text("🤔 Pensando...")
    answer = call_model(question, category="general", title=question)
    if len(answer) > 4000:
        for i in range(0, len(answer), 4000):
            await update.message.reply_text(answer[i:i+4000])
    else:
        await update.message.reply_text(answer)


async def cmd_sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sincroniza dados do Opus."""
    if not _is_authorized(update):
        return
    if not update.message:
        return

    await update.message.reply_text(
        "📡 Cole o JSON de sincronização do Opus:\n"
        '{"decisions":[], "directives":[], "context_updates":{}, "next_tasks":[]}'
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para mensagens de texto (night check-in / sync)."""
    if not _is_authorized(update):
        return
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    # Tentar parsing como JSON (check-in ou sync)
    if text.startswith("{"):
        try:
            data = json.loads(text)

            # Check-in noturno
            if "energy" in data or "genius" in data:
                result = process_night_checkin(
                    completed_quests=[],
                    blocker=data.get("blocker", ""),
                    energy_tomorrow=data.get("energy", 3),
                    good_thing=data.get("good", ""),
                    genius_completed=data.get("genius", False),
                    genius_minutes=data.get("genius_min", 0),
                    non_genius_in_raid=data.get("non_genius", ""),
                )
                await update.message.reply_text(result)
                return

            # Sync do Opus
            if "decisions" in data or "directives" in data:
                result = sync_from_opus(data)
                await update.message.reply_text(result)
                return

        except json.JSONDecodeError:
            pass

    # Mensagem genérica — responder via IA
    answer = call_model(text, category="general", title=text)
    if len(answer) > 4000:
        for i in range(0, len(answer), 4000):
            await update.message.reply_text(answer[i:i+4000])
    else:
        await update.message.reply_text(answer)


def create_bot() -> Application:
    """Cria e configura o bot Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN é obrigatória")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Registrar handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("brief", cmd_brief))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("quests", cmd_quests))
    app.add_handler(CommandHandler("bosses", cmd_bosses))
    app.add_handler(CommandHandler("task", cmd_task))
    app.add_handler(CommandHandler("process", cmd_process))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("ask", cmd_ask))
    app.add_handler(CommandHandler("sync", cmd_sync))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot Telegram configurado com %d handlers", 11)
    return app
