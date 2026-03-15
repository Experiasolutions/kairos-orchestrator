"""
Tools Registry — Catálogo central de ferramentas e APIs do KAIROS SKY.

Fase 3 Arsenal: o polvo precisa de tentáculos.
Este módulo centraliza TUDO que o SKY pode acessar: APIs, MCPs,
ferramentas internas, e serviços externos.

Os agentes (Council, Jarvis Pipeline, bot) consultam este catálogo
para saber o que está disponível antes de planejar ações.
"""
import logging
from datetime import datetime
from typing import TypedDict

import supabase_client as db


logger = logging.getLogger("kairos.tools")


class ToolEntry(TypedDict, total=False):
    """Definição de uma ferramenta/API registrada."""
    tool_id: str
    name: str
    category: str  # api | mcp | internal | media | automation
    status: str    # active | configured | planned | unavailable
    description: str
    endpoint: str
    auth_type: str  # api_key | bearer | none
    rate_limit: str
    monthly_cost: str
    tags: list[str]


# ─── Catálogo Seed ─────────────────────────────────────────

TOOLS_CATALOG: list[ToolEntry] = [
    # ── APIs de IA (Core) ──────────────────────────────────
    {
        "tool_id": "gemini-flash",
        "name": "Google Gemini Flash",
        "category": "api",
        "status": "active",
        "description": "Tasks simples/rápidas: classificação, formatação, respostas curtas.",
        "endpoint": "https://generativelanguage.googleapis.com/v1",
        "auth_type": "api_key",
        "rate_limit": "15 RPM/key (4 keys = 60 RPM)",
        "monthly_cost": "free",
        "tags": ["llm", "fast", "classification"],
    },
    {
        "tool_id": "gemini-high",
        "name": "Google Gemini Pro/High",
        "category": "api",
        "status": "active",
        "description": "Análise complexa, código, arquitetura, raciocínio profundo.",
        "endpoint": "https://generativelanguage.googleapis.com/v1",
        "auth_type": "api_key",
        "rate_limit": "2 RPM/key (4 keys = 8 RPM)",
        "monthly_cost": "free",
        "tags": ["llm", "reasoning", "code"],
    },
    {
        "tool_id": "groq-whisper",
        "name": "Groq Whisper (Transcrição)",
        "category": "api",
        "status": "active",
        "description": "Transcrição de áudio via Whisper large v3 turbo.",
        "endpoint": "https://api.groq.com/openai/v1",
        "auth_type": "api_key",
        "rate_limit": "20 RPM",
        "monthly_cost": "free",
        "tags": ["audio", "transcription", "stt"],
    },
    {
        "tool_id": "groq-llm",
        "name": "Groq LLM (Llama/Mixtral)",
        "category": "api",
        "status": "active",
        "description": "Fallback LLM para dados sensíveis. Ultra-rápido.",
        "endpoint": "https://api.groq.com/openai/v1",
        "auth_type": "api_key",
        "rate_limit": "30 RPM",
        "monthly_cost": "free",
        "tags": ["llm", "fast", "fallback", "sensitive"],
    },

    # ── APIs de Mídia (Planejadas) ─────────────────────────
    {
        "tool_id": "elevenlabs-tts",
        "name": "ElevenLabs TTS",
        "category": "media",
        "status": "planned",
        "description": "Text-to-speech com vozes clonadas. Ideal para conteúdo da Experia.",
        "endpoint": "https://api.elevenlabs.io/v1",
        "auth_type": "api_key",
        "rate_limit": "10K chars/mês (free)",
        "monthly_cost": "free (10K chars) | $5 (30K chars)",
        "tags": ["tts", "voice", "content", "media"],
    },
    {
        "tool_id": "veo3-video",
        "name": "Google Veo 3 (Vídeo)",
        "category": "media",
        "status": "planned",
        "description": "Geração de vídeo por IA. Para conteúdo social da Experia.",
        "endpoint": "https://generativelanguage.googleapis.com/v1",
        "auth_type": "api_key",
        "rate_limit": "N/A",
        "monthly_cost": "free (AI Studio)",
        "tags": ["video", "generation", "content", "media"],
    },
    {
        "tool_id": "flux-image",
        "name": "Flux (Imagem)",
        "category": "media",
        "status": "planned",
        "description": "Geração de imagens. Para posts, thumbnails, assets visuais.",
        "endpoint": "varies",
        "auth_type": "api_key",
        "rate_limit": "N/A",
        "monthly_cost": "free tier varies",
        "tags": ["image", "generation", "content", "media"],
    },

    # ── Automação & Gestão ─────────────────────────────────
    {
        "tool_id": "n8n-workflows",
        "name": "n8n (Self-Hosted)",
        "category": "automation",
        "status": "planned",
        "description": "Automação de workflows: WhatsApp→Supabase, ClickUp triggers, etc.",
        "endpoint": "https://n8n.railway.app (futuro)",
        "auth_type": "bearer",
        "rate_limit": "unlimited (self-hosted)",
        "monthly_cost": "free (Railway/Oracle)",
        "tags": ["automation", "workflow", "webhook", "integration"],
    },
    {
        "tool_id": "clickup-api",
        "name": "ClickUp API",
        "category": "api",
        "status": "planned",
        "description": "Gestão de projetos: criar/atualizar tasks, sprints, timelines.",
        "endpoint": "https://api.clickup.com/api/v2",
        "auth_type": "api_key",
        "rate_limit": "100 RPM",
        "monthly_cost": "free",
        "tags": ["project-management", "tasks", "crm"],
    },
    {
        "tool_id": "vercel-deploy",
        "name": "Vercel (Deploy)",
        "category": "api",
        "status": "planned",
        "description": "Deploy de sites e dashboards. Frontend da Experia e KAIROS Dashboard.",
        "endpoint": "https://api.vercel.com",
        "auth_type": "bearer",
        "rate_limit": "unlimited",
        "monthly_cost": "free (hobby)",
        "tags": ["deploy", "frontend", "hosting"],
    },
    {
        "tool_id": "figma-api",
        "name": "Figma API (Leitura)",
        "category": "api",
        "status": "planned",
        "description": "Ler design tokens, exportar assets. Read-only para design system.",
        "endpoint": "https://api.figma.com/v1",
        "auth_type": "bearer",
        "rate_limit": "unlimited",
        "monthly_cost": "free",
        "tags": ["design", "assets", "tokens"],
    },

    # ── Infraestrutura ─────────────────────────────────────
    {
        "tool_id": "supabase",
        "name": "Supabase (Banco Central)",
        "category": "internal",
        "status": "active",
        "description": "PostgreSQL + Auth + Realtime. 12 tabelas KAIROS + Knowledge Brain.",
        "endpoint": "via SUPABASE_URL env",
        "auth_type": "api_key",
        "rate_limit": "500K rows (free)",
        "monthly_cost": "free | $25 Pro",
        "tags": ["database", "auth", "realtime", "core"],
    },
    {
        "tool_id": "railway",
        "name": "Railway (Servidor)",
        "category": "internal",
        "status": "active",
        "description": "Servidor 24/7 do KAIROS SKY. Python orchestrator + webhook.",
        "endpoint": "https://kairos-sky.up.railway.app",
        "auth_type": "none",
        "rate_limit": "500h/mês (free)",
        "monthly_cost": "free ($5 crédito)",
        "tags": ["server", "hosting", "backend", "core"],
    },
    {
        "tool_id": "telegram-bot",
        "name": "Telegram Bot API",
        "category": "internal",
        "status": "active",
        "description": "Interface principal: 11+ intents, NLP, voice, memory bridge.",
        "endpoint": "https://api.telegram.org",
        "auth_type": "bearer",
        "rate_limit": "30 msg/sec",
        "monthly_cost": "free",
        "tags": ["chat", "interface", "bot", "core"],
    },
    {
        "tool_id": "webhook-receiver",
        "name": "Webhook Receiver (KAIROS)",
        "category": "internal",
        "status": "active",
        "description": "POST /webhook → task_queue. Recebe eventos de n8n, ClickUp, WhatsApp.",
        "endpoint": "https://kairos-sky.up.railway.app/webhook",
        "auth_type": "bearer",
        "rate_limit": "unlimited",
        "monthly_cost": "free",
        "tags": ["webhook", "bridge", "integration"],
    },

    # ── WhatsApp ───────────────────────────────────────────
    {
        "tool_id": "evolution-api",
        "name": "Evolution API (WhatsApp)",
        "category": "api",
        "status": "planned",
        "description": "WhatsApp Business API via Evolution. Para bots de clientes Experia.",
        "endpoint": "self-hosted",
        "auth_type": "api_key",
        "rate_limit": "unlimited (self-hosted)",
        "monthly_cost": "free (self-hosted)",
        "tags": ["whatsapp", "messaging", "client-facing"],
    },
]


# ─── Funções Públicas ──────────────────────────────────────

def get_all_tools() -> list[ToolEntry]:
    """Retorna o catálogo completo de ferramentas."""
    return TOOLS_CATALOG


def get_tools_by_category(category: str) -> list[ToolEntry]:
    """Retorna ferramentas filtradas por categoria."""
    return [t for t in TOOLS_CATALOG if t.get("category") == category]


def get_tools_by_status(status: str) -> list[ToolEntry]:
    """Retorna ferramentas filtradas por status."""
    return [t for t in TOOLS_CATALOG if t.get("status") == status]


def get_active_tools() -> list[ToolEntry]:
    """Retorna apenas ferramentas ativas (configuradas e funcionando)."""
    return get_tools_by_status("active")


def get_tool(tool_id: str) -> ToolEntry | None:
    """Busca uma ferramenta pelo ID."""
    for t in TOOLS_CATALOG:
        if t.get("tool_id") == tool_id:
            return t
    return None


def get_tools_summary() -> str:
    """Retorna resumo do catálogo para injeção em prompts."""
    active = get_tools_by_status("active")
    planned = get_tools_by_status("planned")

    lines: list[str] = [
        "🐙 ARSENAL KAIROS:",
        f"  ✅ {len(active)} ferramentas ativas:",
    ]
    for t in active:
        lines.append(f"    → {t['name']} [{t['category']}]")

    lines.append(f"  📋 {len(planned)} planejadas:")
    for t in planned:
        lines.append(f"    → {t['name']} [{t['category']}]")

    return "\n".join(lines)


def get_media_tools() -> list[ToolEntry]:
    """Retorna ferramentas de mídia (content creation)."""
    return get_tools_by_category("media")


def get_conclave_context() -> str:
    """
    Gera contexto do arsenal para o Conclave/Council.
    O Council precisa saber o que tem disponível para propor soluções viáveis.
    """
    lines = [
        "═══ ARSENAL DISPONÍVEL PARA O CONCLAVE ═══",
        "",
        "ATIVAS (prontas para uso):",
    ]
    for t in get_active_tools():
        lines.append(f"  [{t['tool_id']}] {t['name']}: {t['description']}")
        lines.append(f"    Rate: {t.get('rate_limit', '?')} | Custo: {t.get('monthly_cost', '?')}")

    lines.append("\nPLANEJADAS (disponíveis para ativação):")
    for t in get_tools_by_status("planned"):
        lines.append(f"  [{t['tool_id']}] {t['name']}: {t['description']}")

    lines.append(f"\nTOTAL: {len(TOOLS_CATALOG)} ferramentas no catálogo.")
    lines.append("═════════════════════════════════════════")
    return "\n".join(lines)
