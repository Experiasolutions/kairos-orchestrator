# KAIROS SKY — Composio Bridge
# Ponte para Composio SDK: acesso a 250+ APIs sem gerenciar auth manualmente
# Install: pip install composio-core
import logging
import os

logger = logging.getLogger("kairos.composio_bridge")

# ─── Inicialização ──────────────────────────────────────────

_composio_available = False
_toolset = None


def _init_composio() -> bool:
    """Inicializa a SDK do Composio se disponível."""
    global _composio_available, _toolset  # noqa: PLW0603

    if _composio_available:
        return True

    try:
        from composio import ComposioToolSet

        api_key = os.environ.get("COMPOSIO_API_KEY", "")
        if not api_key:
            logger.warning("COMPOSIO_API_KEY não configurada. Composio desabilitado.")
            return False

        _toolset = ComposioToolSet(api_key=api_key)
        _composio_available = True
        logger.info("✅ Composio SDK inicializado com sucesso")
        return True

    except ImportError:
        logger.warning("Composio SDK não instalado. Run: pip install composio-core")
        return False
    except Exception as e:
        logger.error("Erro ao inicializar Composio: %s", e)
        return False


def is_available() -> bool:
    """Verifica se o Composio está disponível e configurado."""
    return _init_composio()


# ─── Apps Disponíveis ───────────────────────────────────────

# Apps prioritários para o KAIROS SKY
PRIORITY_APPS = {
    # Produtividade
    "gmail": "E-mail — leitura, envio, labels, pesquisa",
    "googlecalendar": "Calendário — eventos, agendamentos, lembretes",
    "googledrive": "Drive — upload, busca, organização de arquivos",
    "googlesheets": "Sheets — leitura, escrita, fórmulas em planilhas",
    "googledocs": "Docs — criação e edição de documentos",

    # CRM & Sales
    "hubspot": "CRM — contatos, deals, pipeline de vendas",
    "salesforce": "CRM Enterprise — leads, oportunidades, contas",

    # Comunicação
    "slack": "Messaging — canais, DMs, notificações",
    "discord": "Community — servidores, canais, bots",
    "telegram": "Messaging — grupos, canais, bots",

    # Desenvolvimento
    "github": "Repos — issues, PRs, actions, webhooks",
    "linear": "Project management — issues, cycles, roadmap",
    "notion": "Wiki — páginas, databases, templates",

    # Social Media
    "twitter": "X/Twitter — posts, trends, analytics",
    "instagram": "Instagram — posts, stories, analytics",
    "linkedin": "LinkedIn — posts, perfis, companhias",

    # Automação
    "zapier": "Automação — triggers, zaps, workflows",
    "airtable": "Base de dados — tabelas, views, automações",

    # Financeiro
    "stripe": "Pagamentos — invoices, subscriptions, charges",
}


def list_priority_apps() -> dict[str, str]:
    """Retorna a lista de apps prioritários para o KAIROS."""
    return PRIORITY_APPS


# ─── Execução de Ações ─────────────────────────────────────

def get_tools_for_app(app_name: str) -> list[dict[str, str]]:
    """
    Retorna as ferramentas disponíveis para um app específico.

    Args:
        app_name: Nome do app (ex: "gmail", "github", "slack")

    Returns:
        Lista de ferramentas com nome e descrição
    """
    if not _init_composio():
        return [{"error": "Composio não disponível"}]

    try:
        from composio import App
        app_enum = getattr(App, app_name.upper(), None)
        if not app_enum:
            return [{"error": f"App '{app_name}' não encontrado"}]

        tools = _toolset.get_tools(apps=[app_enum])
        result: list[dict[str, str]] = []
        for tool in tools:
            result.append({
                "name": str(getattr(tool, "name", "unknown")),
                "description": str(getattr(tool, "description", "")),
            })
        return result

    except Exception as e:
        logger.error("Erro ao buscar tools para '%s': %s", app_name, e)
        return [{"error": str(e)}]


def execute_action(
    app_name: str,
    action_name: str,
    params: dict[str, object] | None = None,
    entity_id: str = "kairos-sky",
) -> dict[str, object]:
    """
    Executa uma ação via Composio.

    Args:
        app_name: Nome do app (ex: "gmail")
        action_name: Nome da ação (ex: "GMAIL_SEND_EMAIL")
        params: Parâmetros da ação
        entity_id: ID da entidade Composio

    Returns:
        Resultado da execução
    """
    if not _init_composio():
        return {"status": "error", "error": "Composio não disponível"}

    try:
        from composio import Action

        action_enum = getattr(Action, action_name.upper(), None)
        if not action_enum:
            return {"status": "error", "error": f"Action '{action_name}' não encontrada"}

        logger.info(
            "🔧 Composio: executando %s.%s (entity=%s)",
            app_name,
            action_name,
            entity_id,
        )

        result = _toolset.execute_action(
            action=action_enum,
            params=params or {},
            entity_id=entity_id,
        )

        return {
            "status": "success",
            "app": app_name,
            "action": action_name,
            "result": result,
        }

    except Exception as e:
        logger.error("Erro na execução Composio: %s", e)
        return {"status": "error", "error": str(e)}


# ─── Integração com crewAI/Swarm ───────────────────────────

def get_crewai_tools(apps: list[str] | None = None) -> list[object]:
    """
    Retorna ferramentas Composio formatadas para uso com crewAI.

    Args:
        apps: Lista de apps (se None, usa os prioritários)

    Returns:
        Lista de tools compatíveis com crewAI
    """
    if not _init_composio():
        return []

    try:
        from composio_crewai import ComposioToolSet as CrewAIToolSet
        from composio import App

        crew_toolset = CrewAIToolSet(api_key=os.environ.get("COMPOSIO_API_KEY", ""))

        if apps:
            app_enums = []
            for app in apps:
                app_enum = getattr(App, app.upper(), None)
                if app_enum:
                    app_enums.append(app_enum)
            return crew_toolset.get_tools(apps=app_enums)
        else:
            # Retorna tools dos apps prioritários
            all_apps = []
            for app_name in PRIORITY_APPS:
                app_enum = getattr(App, app_name.upper(), None)
                if app_enum:
                    all_apps.append(app_enum)
            return crew_toolset.get_tools(apps=all_apps[:5])  # Top 5 para não sobrecarregar

    except ImportError:
        logger.warning("composio-crewai não instalado. Run: pip install composio-crewai")
        return []
    except Exception as e:
        logger.error("Erro ao carregar crewAI tools: %s", e)
        return []


# ─── Status ─────────────────────────────────────────────────

def get_status() -> dict[str, object]:
    """Retorna status completo do Composio."""
    available = _init_composio()
    return {
        "available": available,
        "priority_apps_count": len(PRIORITY_APPS),
        "api_key_configured": bool(os.environ.get("COMPOSIO_API_KEY")),
        "install_command": "pip install composio-core composio-crewai",
    }
