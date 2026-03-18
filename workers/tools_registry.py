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

    # ── Multi-Agent Frameworks ────────────────────────────
    {
        "tool_id": "openai-swarm",
        "name": "OpenAI Swarm",
        "category": "internal",
        "status": "planned",
        "description": "Framework experimental de multi-agent com handoffs dinâmicos e context variables. Leve, stateless, testável.",
        "endpoint": "pip://git+https://github.com/openai/swarm.git",
        "auth_type": "api_key",
        "rate_limit": "depende do modelo OpenAI/compatível",
        "monthly_cost": "free (open source)",
        "tags": ["multi-agent", "swarm", "handoffs", "orchestration"],
    },
    {
        "tool_id": "openai-agents-sdk",
        "name": "OpenAI Agents SDK",
        "category": "internal",
        "status": "planned",
        "description": "Successor production-ready do Swarm. Agents, handoffs, guardrails. Recommended para produção.",
        "endpoint": "pip://openai-agents",
        "auth_type": "api_key",
        "rate_limit": "depende do modelo",
        "monthly_cost": "free (open source)",
        "tags": ["multi-agent", "production", "guardrails", "handoffs"],
    },
    {
        "tool_id": "crewai-framework",
        "name": "crewAI",
        "category": "internal",
        "status": "planned",
        "description": "Framework multi-agent com roles, goals, backstory. Motor principal dos SKY Squads.",
        "endpoint": "pip://crewai",
        "auth_type": "api_key",
        "rate_limit": "depende do modelo",
        "monthly_cost": "free (open source)",
        "tags": ["multi-agent", "crew", "roles", "squads"],
    },
    {
        "tool_id": "compound-engineering",
        "name": "Compound Engineering (Swarm Skills)",
        "category": "internal",
        "status": "active",
        "description": "Pipeline de IA com skill 'orchestrating-swarms'. Já no disco em tools/integrations/.",
        "endpoint": "local://tools/integrations/compound-engineering",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["pipeline", "swarm", "skills", "compound"],
    },


    # ██ OPENCLAW — FERRAMENTA PRINCIPAL DO SISTEMA ██
    # ══════════════════════════════════════════════════════
    {
        "tool_id": "openclaw-platform",
        "name": "OpenClaw (AI Assistant Platform)",
        "category": "internal",
        "status": "active",
        "description": "Plataforma principal de execução autônoma. Gateway WS, 22+ canais, Skills, browser control, multi-agent routing, sandbox Docker.",
        "endpoint": "ws://127.0.0.1:18789",
        "auth_type": "bearer",
        "rate_limit": "unlimited (local)",
        "monthly_cost": "free (self-hosted)",
        "tags": ["core", "agent", "execution", "multi-channel", "skills"],
    },

    # ─── ClawHub Skills: Mãos (Produtividade) ─────────────
    {
        "tool_id": "claw-gog",
        "name": "Gog (Google Workspace)",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Gmail, Calendar, Drive, Docs e Sheets centralizados.",
        "endpoint": "clawhub://gog",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["google", "email", "calendar", "productivity"],
    },
    {
        "tool_id": "claw-github",
        "name": "GitHub Integration",
        "category": "openclaw-skill",
        "status": "active",
        "description": "Gestão de repositórios, issues e code reviews.",
        "endpoint": "clawhub://github",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["github", "code", "issues", "devops"],
    },
    {
        "tool_id": "claw-n8n",
        "name": "n8n Workflow Skill",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Interface de voz/texto para automações complexas no n8n.",
        "endpoint": "clawhub://n8n-workflow",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["automation", "workflow", "n8n"],
    },
    {
        "tool_id": "n8n-mcp",
        "name": "n8n-MCP (Antigravity Bridge)",
        "category": "internal",
        "status": "planned",
        "description": "MCP server para n8n. Antigravity controla workflows n8n diretamente. Requer VPS free tier com instância n8n.",
        "endpoint": "mcp://n8n-vps",
        "auth_type": "api_key",
        "rate_limit": "unlimited (self-hosted)",
        "monthly_cost": "free (VPS free tier)",
        "tags": ["mcp", "n8n", "antigravity", "automation", "vps"],
    },
    {
        "tool_id": "railway-bridge",
        "name": "Railway Bridge (Criador de Tentáculos)",
        "category": "internal",
        "status": "active",
        "description": "15 OpenClaw Skills para controle total do Railway. 4 Tiers: Deployment, Observability, Storage, Orchestration. Provisiona infraestrutura autônoma. O 'Polvo' do KAIROS.",
        "endpoint": "bridges/railway_bridge.py",
        "auth_type": "bearer_token",
        "rate_limit": "Railway API limits",
        "monthly_cost": "Railway plan",
        "tags": ["railway", "infrastructure", "deploy", "openclaw", "hydra", "polvo", "auto-heal", "tentacles"],
    },
    {
        "tool_id": "experia-mcp-server",
        "name": "Experia MCP Server (FastAPI)",
        "category": "internal",
        "status": "active",
        "description": "16 tools MCP: n8n workflows (4), database (3), client management (4), infrastructure (3), webhooks (2). Bridge Antigravity ↔ Railway Hydra.",
        "endpoint": "mcp_server/mcp_server.py",
        "auth_type": "api_key",
        "rate_limit": "unlimited (self-hosted)",
        "monthly_cost": "Railway plan",
        "tags": ["mcp", "fastapi", "n8n", "postgres", "infrastructure", "multi-tenant", "hydra"],
    },
    {
        "tool_id": "claw-trello",
        "name": "Trello",
        "category": "openclaw-skill",
        "status": "active",
        "description": "Gestão de projetos e tickets via Trello.",
        "endpoint": "clawhub://trello",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["project-management", "tasks", "kanban"],
    },
    {
        "tool_id": "claw-agentmail",
        "name": "Agentmail",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Dá identidade de e-mail própria ao agente para comunicação externa.",
        "endpoint": "clawhub://agentmail",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["email", "identity", "communication"],
    },
    {
        "tool_id": "composio-sdk",
        "name": "Composio SDK (250+ APIs)",
        "category": "internal",
        "status": "active",
        "description": "SDK integrada via composio_bridge.py. 250+ APIs: Gmail, GitHub, Slack, Salesforce, Stripe, HubSpot, etc. Auth gerenciada.",
        "endpoint": "pip://composio-core",
        "auth_type": "api_key",
        "rate_limit": "depende do app",
        "monthly_cost": "free (open source)",
        "tags": ["integration", "bridge", "multi-app", "sdk", "250-apis"],
    },

    # ─── ClawHub Skills: Sentidos (Navegação & Pesquisa) ──
    {
        "tool_id": "claw-firecrawl",
        "name": "Firecrawl CLI",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Extração de conteúdo limpo (Markdown) de sites complexos.",
        "endpoint": "clawhub://firecrawl-cli",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["scraping", "web", "extraction", "markdown"],
    },
    {
        "tool_id": "claw-felo-search",
        "name": "Felo Search",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Pesquisa com síntese de IA e citações diretas.",
        "endpoint": "clawhub://felo-search",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["search", "ai-synthesis", "research"],
    },
    {
        "tool_id": "claw-exa-search",
        "name": "Exa Search",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Motor de busca focado em documentação técnica e código.",
        "endpoint": "clawhub://exa-search",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["search", "technical", "code", "docs"],
    },
    {
        "tool_id": "claw-brave-search",
        "name": "Brave Search",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Resultados otimizados para consumo de IA (baixo ruído).",
        "endpoint": "clawhub://brave-search",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["search", "web", "low-noise"],
    },
    {
        "tool_id": "claw-xclaw",
        "name": "XClaw-Skill (Twitter/X)",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Monitoramento de tendências e influenciadores no X (Twitter).",
        "endpoint": "clawhub://xclaw-skill",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["social-media", "twitter", "trends", "monitoring"],
    },
    {
        "tool_id": "claw-playwright",
        "name": "Playwright-MCP",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Navegação autônoma e interação com sites (clicar, preencher, scraping).",
        "endpoint": "clawhub://playwright-mcp",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["browser", "automation", "scraping", "interaction"],
    },

    # ─── ClawHub Skills: Cérebro (Inteligência & Memória) ─
    {
        "tool_id": "claw-self-improving",
        "name": "Self-Improving Agent",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Aprendizado contínuo com erros e correções passadas.",
        "endpoint": "clawhub://self-improving-agent",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["learning", "self-improvement", "evolution"],
    },
    {
        "tool_id": "claw-ontology",
        "name": "Ontology",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Gráficos de conhecimento sobre relações complexas.",
        "endpoint": "clawhub://ontology",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["knowledge-graph", "reasoning", "relations"],
    },
    {
        "tool_id": "claw-memory-hygiene",
        "name": "Memory Hygiene",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Limpeza de contextos obsoletos para evitar alucinações.",
        "endpoint": "clawhub://memory-hygiene",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["memory", "cleanup", "anti-hallucination"],
    },
    {
        "tool_id": "claw-auto-workflows",
        "name": "Automation-Workflows",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Agente cria suas próprias automações sob demanda.",
        "endpoint": "clawhub://automation-workflows",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["automation", "self-service", "meta"],
    },
    {
        "tool_id": "claw-mcp-builder",
        "name": "MCP-Builder",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Ensina o agente a criar novos conectores (servidores MCP) para APIs.",
        "endpoint": "clawhub://mcp-builder",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["mcp", "builder", "connectors", "meta"],
    },
    {
        "tool_id": "claw-optimizer",
        "name": "OpenClaw-Optimizer",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Redução drástica de custo de tokens via compressão de contexto.",
        "endpoint": "clawhub://openclaw-optimizer",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["optimization", "tokens", "cost-reduction"],
    },

    # ─── ClawHub Skills: Talentos (Multimídia) ────────────
    {
        "tool_id": "claw-whisper",
        "name": "OpenAI Whisper (local)",
        "category": "openclaw-skill",
        "status": "active",
        "description": "Transcrição de áudio local e privada.",
        "endpoint": "clawhub://openai-whisper",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["audio", "transcription", "stt", "local"],
    },
    {
        "tool_id": "claw-elevenlabs",
        "name": "ElevenLabs Agent",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Voz para o agente e capacidade de realizar chamadas telefônicas.",
        "endpoint": "clawhub://eleven-labs-agent",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free tier",
        "tags": ["tts", "voice", "phone-calls"],
    },
    {
        "tool_id": "claw-video-agent",
        "name": "Video-Agent (HeyGen)",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Geração de vídeos com avatares realistas.",
        "endpoint": "clawhub://video-agent",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free tier",
        "tags": ["video", "avatar", "content"],
    },
    {
        "tool_id": "claw-polyclaw",
        "name": "Polyclaw",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Análise de mercados preditivos e execução de estratégias.",
        "endpoint": "clawhub://polyclaw",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["markets", "prediction", "strategy"],
    },

    # ─── ClawHub Skills: Escudo (Segurança) ───────────────
    {
        "tool_id": "claw-skillguard",
        "name": "SkillGuard",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Auditoria obrigatória de permissões antes de instalações.",
        "endpoint": "clawhub://skillguard",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["security", "audit", "permissions"],
    },
    {
        "tool_id": "claw-skill-vetter",
        "name": "Azhua-Skill-Vetter",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Escaneia skills em busca de malware ou vazamento de dados.",
        "endpoint": "clawhub://azhua-skill-vetter",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["security", "malware-scan", "vetting"],
    },
    {
        "tool_id": "claw-0protocol",
        "name": "0Protocol",
        "category": "openclaw-skill",
        "status": "planned",
        "description": "Gestão segura de identidades e rotação de credenciais.",
        "endpoint": "clawhub://0protocol",
        "auth_type": "none",
        "rate_limit": "N/A",
        "monthly_cost": "free",
        "tags": ["security", "identity", "credentials"],
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
    openclaw_skills = get_tools_by_category("openclaw-skill")

    lines: list[str] = [
        "🐙 ARSENAL KAIROS:",
        f"  ✅ {len(active)} ferramentas ativas:",
    ]
    for t in active:
        lines.append(f"    → {t['name']} [{t['category']}]")

    lines.append(f"  📋 {len(planned)} planejadas:")
    for t in planned:
        lines.append(f"    → {t['name']} [{t['category']}]")

    lines.append(f"  🦞 {len(openclaw_skills)} OpenClaw skills mapeadas")

    return "\n".join(lines)


def get_media_tools() -> list[ToolEntry]:
    """Retorna ferramentas de mídia (content creation)."""
    return get_tools_by_category("media")


def get_openclaw_skills() -> list[ToolEntry]:
    """Retorna todas as skills OpenClaw/ClawHub catalogadas."""
    return get_tools_by_category("openclaw-skill")


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
