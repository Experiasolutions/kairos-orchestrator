# Telegram Bot — KAIROS SKY (Natural Language Interface)
# O Gabriel conversa naturalmente e o SKY entende a intenção.
import logging
import json
import io
from groq import Groq
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GROQ_API_KEY
from persona import SYSTEM_PROMPT
from workers.morning_brief import generate_morning_brief
from workers.night_processor import process_night_checkin
from workers.context_sync import sync_from_opus, get_system_status
from workers.task_worker import process_pending_tasks, call_model
from workers.os_worker import get_os_status, check_zone_violation
import supabase_client as db
from supabase_client import save_memory, get_recent_memories

logger = logging.getLogger("kairos.telegram")

# ─── Intent Classifier (Rápido, sem LLM) ─────────────────────

INTENT_KEYWORDS = {
    "brief": ["brief", "briefing", "matinal", "morning", "relatório", "relatorio", "resumo do dia", "como estão as coisas"],
    "status": ["status", "como estou", "como estamos", "nivel", "nível", "xp", "season", "sistema", "como está o sistema", "como ta"],
    "quests": ["quest", "missão", "missões", "missoes", "tarefas de hoje", "o que tenho", "o que fazer", "afazeres"],
    "bosses": ["boss", "bosses", "dívida", "divida", "dívidas", "dividas", "financeiro", "quanto devo", "finanças"],
    "add_task": ["adiciona task", "adicionar task", "nova task", "cria task", "adiciona tarefa", "nova tarefa", "anota", "anota aí", "lembra de"],
    "process": ["processa", "processar", "executa task", "executar", "roda as tasks", "processa as tasks"],
    "checkin": ["check-in", "checkin", "check in", "noturno", "encerrar o dia", "finalizar dia", "como foi o dia"],
    "leads": ["lead", "leads", "clientes", "prospectos", "pipeline"],
    "bloco": ["bloco", "zona", "qual bloco", "que zona", "que horas", "raid", "aurora", "santuário", "santuario", "vórtex", "vortex", "agenda", "cronograma"],
    "lembrar": ["lembra disso", "guarda isso", "salva isso", "anota isso", "lembra que", "guarda que", "salva que", "não esquece", "memoriza", "registra isso", "registra que"],
    "memoria": ["o que você lembra", "minhas notas", "memórias", "o que eu disse", "o que guardei", "recorda", "histórico"],
    "arsenal": ["arsenal", "ferramentas", "tools", "apis", "integrações", "integracoes", "o que temos", "capacidades"],
    "conclave": ["conclave", "council", "conselho", "convocar conselho", "auditar", "auditoria", "convoca o conselho", "hive mind"],
}


def _classify_intent(text: str) -> str:
    """Classifica a intenção do Gabriel via keywords simples (zero latência)."""
    text_lower = text.lower().strip()

    # Checagem rápida de keywords
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return intent

    # Se não bater nenhum keyword, é conversa livre (vai pro LLM)
    return "conversation"


# ─── Auth ─────────────────────────────────────────────────────

def _is_authorized(update: Update) -> bool:
    """Verifica se o usuário é o Gabriel."""
    chat_id = str(update.effective_chat.id) if update.effective_chat else ""
    if TELEGRAM_CHAT_ID and chat_id != TELEGRAM_CHAT_ID:
        logger.warning("Acesso não autorizado: chat_id=%s", chat_id)
        return False
    return True


# ─── Action Executors ─────────────────────────────────────────

async def _exec_brief(update: Update) -> None:
    """Gera e envia o Morning Brief."""
    if not update.message:
        return
    await update.message.reply_text("⏳ Preparando seu briefing, Dragonborn...")
    brief = generate_morning_brief()
    await _send_long(update, brief)


async def _exec_status(update: Update) -> None:
    """Mostra status do sistema + saúde do KAIROS."""
    if not update.message:
        return
    status = get_system_status()
    # Adicionar health report do system auditor
    try:
        from workers.system_auditor import format_health_report
        health = format_health_report()
        status += "\n\n" + health
    except Exception:
        pass
    await _send_long(update, status)


async def _exec_quests(update: Update) -> None:
    """Lista missões de hoje."""
    if not update.message:
        return
    quests = db.get_today_quests()
    if not quests:
        await update.message.reply_text("📋 Nenhuma missão definida para hoje.\nMe diga o que quer fazer e eu crio uma!")
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


async def _exec_bosses(update: Update) -> None:
    """Lista bosses financeiros."""
    if not update.message:
        return
    bosses = db.get_bosses()
    if not bosses:
        await update.message.reply_text("🎉 Todos os bosses derrotados! Zerou o jogo!")
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


async def _exec_lembrar(update: Update, text: str) -> None:
    """Salva uma memória no Knowledge Brain (ponte Telegram→Antigravity)."""
    if not update.message:
        return
    # Remover keywords de ativação
    clean = text
    for kw in ["lembra disso", "guarda isso", "salva isso", "anota isso",
               "lembra que", "guarda que", "salva que", "não esquece",
               "memoriza", "registra isso", "registra que"]:
        clean = clean.lower().replace(kw, "").strip()

    if not clean or len(clean) < 3:
        await update.message.reply_text("🤔 O que você quer que eu lembre?")
        return

    # Detectar categoria por keywords simples
    category = "telegram_note"
    cat_keywords = {
        "decisao": ["decidi", "decisão", "escolhi", "optei"],
        "ideia": ["ideia", "insight", "pensei", "tive uma"],
        "financeiro": ["paguei", "recebi", "divida", "dívida", "boleto", "dinheiro", "reais", "r$"],
        "cliente": ["cliente", "elaine", "hortifruti", "master pumps", "lead", "proposta"],
        "pessoal": ["letícia", "saúde", "treino", "maconha", "sentimento"],
    }
    clean_lower = clean.lower()
    for cat, kws in cat_keywords.items():
        for kw in kws:
            if kw in clean_lower:
                category = cat
                break

    tags = ["telegram", category, "dragonborn"]
    result = save_memory(clean, category=category, tags=tags)
    if result:
        await update.message.reply_text(
            f"🧠 Memorizado [{category}]: *{clean[:80]}*\n"
            f"✅ Guardado no Knowledge Brain. O Antigravity vai saber disso.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("❌ Erro ao salvar memória. Tenta de novo.")


async def _exec_memoria(update: Update) -> None:
    """Mostra memórias recentes do Knowledge Brain."""
    if not update.message:
        return
    memories = get_recent_memories(limit=10)
    if not memories:
        await update.message.reply_text("🧠 Nenhuma memória salva ainda. Use 'lembra que...' para guardar algo.")
        return

    lines = ["🧠 *MEMÓRIAS RECENTES:*\n"]
    for m in memories:
        created = m.get("created_at", "")[:10]
        category = m.get("category", "?")
        summary = m.get("summary", "")[:80]
        lines.append(f"📌 [{category}] {summary} _({created})_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def _exec_bloco(update: Update) -> None:
    """Mostra o bloco de tempo atual da OS."""
    if not update.message:
        return
    status = get_os_status()
    await update.message.reply_text(status)


async def _exec_add_task(update: Update, text: str) -> None:
    """Adiciona task à fila extraindo a descrição do texto natural."""
    if not update.message:
        return
    # Remove keywords de ativação para pegar só a descrição
    clean = text
    for kw in ["adiciona task", "adicionar task", "nova task", "cria task",
                "adiciona tarefa", "nova tarefa", "anota aí", "anota", "lembra de"]:
        clean = clean.lower().replace(kw, "").strip()

    if not clean or len(clean) < 3:
        await update.message.reply_text("🤔 O que você quer que eu anote como task?")
        return

    # Verificar se a task viola a zona atual
    violation = check_zone_violation(clean)
    if violation:
        await update.message.reply_text(violation)

    db.add_task(clean, created_by="gabriel")
    await update.message.reply_text(f"✅ Anotado: *{clean}*\nVou processar quando chegar a hora.", parse_mode="Markdown")


async def _exec_process(update: Update) -> None:
    """Processa tasks pendentes."""
    if not update.message:
        return
    await update.message.reply_text("⏳ Processando tasks pendentes...")
    results = process_pending_tasks()
    if not results:
        await update.message.reply_text("📋 Fila limpa, nenhuma task pendente.")
        return

    completed = sum(1 for r in results if r.get("status") == "completed")
    failed = sum(1 for r in results if r.get("status") == "failed")
    await update.message.reply_text(f"✅ {completed} concluídas | ❌ {failed} falharam")


async def _exec_checkin(update: Update) -> None:
    """Inicia night check-in conversacional."""
    if not update.message:
        return
    msg = (
        "🌙 Bora fechar o dia, Dragonborn.\n\n"
        "Me conta:\n"
        "1. O que bloqueou hoje?\n"
        "2. Energia pra amanhã (1-5)?\n"
        "3. Uma coisa boa do dia?\n"
        "4. Fez algo na zona 🔵 (gênio)? Quanto tempo?\n\n"
        "Pode mandar em texto livre que eu entendo."
    )
    await update.message.reply_text(msg)


async def _exec_leads(update: Update) -> None:
    """Lista leads ativos."""
    if not update.message:
        return
    leads = db.get_leads()
    if not leads:
        await update.message.reply_text("📭 Nenhum lead no pipeline ainda.")
        return

    lines = [f"📊 LEADS ATIVOS ({len(leads)})\n"]
    for lead in leads[:10]:
        status_icon = {"new": "🆕", "contacted": "📞", "qualified": "✅", "lost": "❌"}.get(
            lead.get("status", "new"), "⚪"
        )
        lines.append(f"{status_icon} {lead.get('name', 'Sem nome')} — {lead.get('source', '?')}")

    if len(leads) > 10:
        lines.append(f"\n... e mais {len(leads) - 10} leads")
    await update.message.reply_text("\n".join(lines))


async def _exec_arsenal(update: Update) -> None:
    """Mostra o catálogo de ferramentas e APIs disponíveis."""
    if not update.message:
        return
    try:
        from workers.tools_registry import get_tools_summary
        summary = get_tools_summary()
        await update.message.reply_text(summary)
    except Exception as e:
        await update.message.reply_text(f"Erro ao carregar arsenal: {e}")


async def _exec_conclave(update: Update) -> None:
    """Convoca o IA Council sob demanda."""
    if not update.message:
        return
    await update.message.reply_text("🏛️ Convocando o Conclave KAIROS... (3 cadeiras deliberando)")
    try:
        from workers.council_auditor import convene_council
        report = convene_council()
        await _send_long(update, report)
    except Exception as e:
        await update.message.reply_text(f"Erro ao convocar Council: {e}")


async def _exec_conversation(update: Update, text: str) -> None:
    """Conversa livre — envia pro LLM com contexto do Knowledge Brain."""
    if not update.message:
        return

    # Tentar parsing como JSON (check-in ou sync legado)
    if text.strip().startswith("{"):
        try:
            data = json.loads(text)
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
            if "decisions" in data or "directives" in data:
                result = sync_from_opus(data)
                await update.message.reply_text(result)
                return
        except json.JSONDecodeError:
            pass

    # Conversa livre com LLM — enriquecida com Knowledge Brain + memórias + estado cognitivo
    brain_context = ""
    try:
        from supabase_client import get_brain_context, get_recent_memories
        # Buscar conhecimento relevante ao que Gabriel disse
        brain_context = get_brain_context(text, max_chunks=3)
        # Adicionar últimas memórias do dia como contexto
        recent = get_recent_memories(limit=3)
        if recent:
            mem_lines = ["\n--- MEMÓRIAS RECENTES DO GABRIEL ---"]
            for m in recent:
                mem_lines.append(f"[{m.get('category', '?')}] {m.get('content_chunk', '')}")
            mem_lines.append("--- FIM MEMÓRIAS ---\n")
            brain_context += "\n".join(mem_lines)
    except Exception:
        pass  # Se falhar, continua sem contexto extra

    # Injetar estado cognitivo (Noesis Layer 1)
    try:
        from workers.cognitive_state import get_state_summary
        cognitive = get_state_summary()
        if cognitive:
            brain_context += f"\n\n--- ESTADO COGNITIVO ---\n{cognitive}\n--- FIM ESTADO ---\n"
    except Exception:
        pass

    enriched = f"{SYSTEM_PROMPT}\n\n{brain_context}\n\nGabriel disse: {text}"
    answer = call_model(enriched, category="general", title=text)
    await _send_long(update, answer)


# ─── Utilities ────────────────────────────────────────────────

async def _send_long(update: Update, text: str) -> None:
    """Envia mensagem longa quebrando em chunks de 4000 chars."""
    if not update.message:
        return
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            await update.message.reply_text(text[i:i+4000])
    else:
        await update.message.reply_text(text)


async def _transcribe_voice(file_bytes: bytes) -> str:
    """Transcreve áudio via Groq Whisper (distil-whisper-large-v3-en)."""
    if not GROQ_API_KEY:
        return "[Transcrição indisponível — key Groq não configurada]"
    try:
        client = Groq(api_key=GROQ_API_KEY)
        transcription = client.audio.transcriptions.create(
            file=("voice.ogg", file_bytes),
            model="whisper-large-v3-turbo",
            language="pt",
        )
        return transcription.text
    except Exception as e:
        logger.error("Erro na transcrição: %s", e)
        return f"[Erro na transcrição: {e}]"


# ─── Main Handler (O Cérebro de Roteamento) ──────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Único /command mantido — bootstrap inicial."""
    if not _is_authorized(update):
        return
    if not update.message:
        return

    chat_id = update.effective_chat.id if update.effective_chat else "unknown"
    msg = (
        "🐉 KAIROS SKY — Online\n\n"
        f"Chat ID: `{chat_id}`\n\n"
        "Eu entendo linguagem natural. Exemplos:\n"
        '• "Me dá o briefing do dia"\n'
        '• "Como estão minhas finanças?"\n'
        '• "Quais tarefas tenho pra hoje?"\n'
        '• "Anota aí: ligar pro hortifruti amanhã"\n'
        '• "Status do sistema"\n'
        '• "Quantos leads eu tenho?"\n\n'
        "Pode falar comigo como se fosse um chat normal. 🎯"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def _route_intent(update: Update, text: str) -> None:
    """Roteia texto classificado para a ação correta."""
    intent = _classify_intent(text)
    logger.info("Mensagem: '%s' → Intent: %s", text[:50], intent)

    if intent == "brief":
        await _exec_brief(update)
    elif intent == "status":
        await _exec_status(update)
    elif intent == "quests":
        await _exec_quests(update)
    elif intent == "bosses":
        await _exec_bosses(update)
    elif intent == "add_task":
        await _exec_add_task(update, text)
    elif intent == "process":
        await _exec_process(update)
    elif intent == "checkin":
        await _exec_checkin(update)
    elif intent == "leads":
        await _exec_leads(update)
    elif intent == "bloco":
        await _exec_bloco(update)
    elif intent == "lembrar":
        await _exec_lembrar(update, text)
    elif intent == "memoria":
        await _exec_memoria(update)
    elif intent == "arsenal":
        await _exec_arsenal(update)
    elif intent == "conclave":
        await _exec_conclave(update)
    else:
        await _exec_conversation(update, text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para mensagens de texto."""
    if not _is_authorized(update):
        return
    if not update.message or not update.message.text:
        return
    await _route_intent(update, update.message.text.strip())


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para mensagens de voz — transcreve via Groq Whisper e processa."""
    if not _is_authorized(update):
        return
    if not update.message:
        return

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    logger.info("Áudio recebido (%d bytes, %ss)", voice.file_size or 0, voice.duration or 0)
    await update.message.reply_text("🎧 Transcrevendo seu áudio...")

    try:
        tg_file = await voice.get_file()
        file_bytes = await tg_file.download_as_bytearray()
        transcript = await _transcribe_voice(bytes(file_bytes))

        if transcript.startswith("["):
            # Erro na transcrição
            await update.message.reply_text(transcript)
            return

        # Mostrar transcrição e processar
        await update.message.reply_text(f"📝 *Transcrição:* {transcript}", parse_mode="Markdown")
        # Prefixar com tag para que o LLM saiba que é transcrição e não peça de volta
        tagged = f"[ÁUDIO TRANSCRITO] {transcript}"
        await _route_intent(update, tagged)

    except Exception as e:
        logger.error("Erro ao processar áudio: %s", e)
        await update.message.reply_text(f"❌ Erro ao processar áudio: {e}")


# ─── Bot Factory ──────────────────────────────────────────────

def create_bot() -> Application:
    """Cria e configura o bot Telegram (Natural Language + Voice)."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN é obrigatória")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # /start é o único command (bootstrap)
    app.add_handler(CommandHandler("start", cmd_start))

    # Texto: linguagem natural
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Áudio: transcrição via Groq Whisper + processamento
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    logger.info("Bot Telegram configurado: Natural Language + Voice (3 handlers)")
    return app
