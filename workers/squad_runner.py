# KAIROS SKY — Squad Runner
# Motor de squads autônomos para execução distribuída
# Suporta crewAI como motor principal, com fallback para OpenAI Swarm
import asyncio
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("kairos.squad_runner")

# ─── Tipos ──────────────────────────────────────────────────

SQUAD_CONFIGS: dict[str, dict[str, object]] = {
    "research": {
        "name": "Research Squad",
        "description": "Pesquisa, análise e síntese de informações",
        "agents": [
            {
                "role": "Researcher",
                "goal": "Encontrar informações relevantes e confiáveis",
                "backstory": "Especialista em pesquisa que encontra dados precisos rapidamente.",
            },
            {
                "role": "Analyst",
                "goal": "Analisar e sintetizar informações em insights acionáveis",
                "backstory": "Analista que transforma dados brutos em decisões claras.",
            },
        ],
        "process": "sequential",
    },
    "sales": {
        "name": "Sales Squad",
        "description": "Prospecção, qualificação de leads e follow-up",
        "agents": [
            {
                "role": "Lead Qualifier",
                "goal": "Qualificar leads pelo potencial de conversão",
                "backstory": "BDR experiente que identifica oportunidades reais.",
            },
            {
                "role": "Check-up Digital",
                "goal": "Analisar presença digital do lead e gerar relatório",
                "backstory": "Especialista em auditoria digital que gera valor imediato.",
            },
            {
                "role": "Follow-up Agent",
                "goal": "Manter contato e avançar o lead no funil",
                "backstory": "Closer que sabe o momento certo de agir.",
            },
        ],
        "process": "sequential",
    },
    "content": {
        "name": "Content Squad",
        "description": "Criação de conteúdo para redes sociais e blog",
        "agents": [
            {
                "role": "Content Strategist",
                "goal": "Definir temas e formatos que geram engajamento",
                "backstory": "Estrategista de conteúdo com foco em conversão.",
            },
            {
                "role": "Content Writer",
                "goal": "Produzir conteúdo original e atraente",
                "backstory": "Copywriter que escreve para humanos reais.",
            },
        ],
        "process": "sequential",
    },
    "code": {
        "name": "Code Squad",
        "description": "Desenvolvimento de código e code review",
        "agents": [
            {
                "role": "Developer",
                "goal": "Implementar funcionalidades com código limpo",
                "backstory": "Dev fullstack que prioriza simplicidade e robustez.",
            },
            {
                "role": "Code Reviewer",
                "goal": "Garantir qualidade e segurança do código",
                "backstory": "QA que encontra bugs antes dos usuários.",
            },
        ],
        "process": "sequential",
    },
}


# ─── Motor de Execução ──────────────────────────────────────

def _get_engine() -> str:
    """Detecta qual motor multi-agent está disponível."""
    try:
        import crewai  # noqa: F401
        return "crewai"
    except ImportError:
        pass

    try:
        import swarm  # noqa: F401
        return "swarm"
    except ImportError:
        pass

    return "fallback"


async def run_squad_crewai(
    squad_id: str,
    task_description: str,
    model: str = "gemini/gemini-2.0-flash",
) -> dict[str, object]:
    """Executa um squad usando crewAI."""
    from crewai import Agent, Crew, Process, Task

    config = SQUAD_CONFIGS.get(squad_id)
    if not config:
        return {"error": f"Squad '{squad_id}' não encontrado", "status": "failed"}

    agents_list = config.get("agents", [])
    crew_agents: list[Agent] = []

    for agent_cfg in agents_list:
        agent_dict = dict(agent_cfg) if isinstance(agent_cfg, dict) else {}
        agent = Agent(
            role=str(agent_dict.get("role", "Agent")),
            goal=str(agent_dict.get("goal", "")),
            backstory=str(agent_dict.get("backstory", "")),
            verbose=True,
            llm=model,
        )
        crew_agents.append(agent)

    tasks: list[Task] = []
    for i, agent in enumerate(crew_agents):
        task = Task(
            description=f"[{agent.role}] {task_description}",
            expected_output=f"Resultado detalhado da tarefa assignada ao {agent.role}",
            agent=agent,
        )
        tasks.append(task)

    process_type = (
        Process.sequential
        if str(config.get("process", "sequential")) == "sequential"
        else Process.hierarchical
    )

    crew = Crew(
        agents=crew_agents,
        tasks=tasks,
        process=process_type,
        verbose=True,
    )

    logger.info("🚀 Squad '%s' iniciando com crewAI (%d agents)", squad_id, len(crew_agents))

    result = crew.kickoff()
    return {
        "squad_id": squad_id,
        "engine": "crewai",
        "status": "completed",
        "result": str(result),
        "agents_count": len(crew_agents),
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


async def run_squad_swarm(
    squad_id: str,
    task_description: str,
) -> dict[str, object]:
    """Executa um squad usando OpenAI Swarm."""
    from swarm import Agent, Swarm

    config = SQUAD_CONFIGS.get(squad_id)
    if not config:
        return {"error": f"Squad '{squad_id}' não encontrado", "status": "failed"}

    client = Swarm()
    agents_list = config.get("agents", [])

    swarm_agents: list[Agent] = []
    for agent_cfg in agents_list:
        agent_dict = dict(agent_cfg) if isinstance(agent_cfg, dict) else {}
        agent = Agent(
            name=str(agent_dict.get("role", "Agent")),
            instructions=f"Você é {agent_dict.get('role', 'Agent')}. {agent_dict.get('backstory', '')}. Seu objetivo: {agent_dict.get('goal', '')}",
        )
        swarm_agents.append(agent)

    logger.info("🚀 Squad '%s' iniciando com Swarm (%d agents)", squad_id, len(swarm_agents))

    results: list[str] = []
    messages = [{"role": "user", "content": task_description}]

    for agent in swarm_agents:
        response = client.run(agent=agent, messages=messages)
        last_message = response.messages[-1] if response.messages else None
        agent_result = str(last_message.get("content", "")) if last_message else ""
        results.append(f"[{agent.name}] {agent_result}")
        messages.append({"role": "assistant", "content": agent_result})

    return {
        "squad_id": squad_id,
        "engine": "swarm",
        "status": "completed",
        "result": "\n\n".join(results),
        "agents_count": len(swarm_agents),
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


async def run_squad_fallback(
    squad_id: str,
    task_description: str,
) -> dict[str, object]:
    """Fallback: executa squad via chamada direta ao Gemini (sem framework)."""
    config = SQUAD_CONFIGS.get(squad_id)
    if not config:
        return {"error": f"Squad '{squad_id}' não encontrado", "status": "failed"}

    logger.info(
        "🚀 Squad '%s' iniciando em modo fallback (API direta)", squad_id,
    )

    agents_list = config.get("agents", [])
    agent_descriptions: list[str] = []
    for agent_cfg in agents_list:
        agent_dict = dict(agent_cfg) if isinstance(agent_cfg, dict) else {}
        agent_descriptions.append(
            f"- {agent_dict.get('role', 'Agent')}: {agent_dict.get('goal', '')} ({agent_dict.get('backstory', '')})"
        )

    prompt = (
        f"Você é o squad '{config.get('name', squad_id)}' composto por estes agentes:\n"
        f"{'chr(10)'.join(agent_descriptions)}\n\n"
        f"Tarefa: {task_description}\n\n"
        f"Simule a execução sequencial de cada agente, "
        f"mostrando a contribuição individual de cada um."
    )

    # Usar model router do KAIROS
    try:
        from workers.task_worker import call_gemini
        result = call_gemini(prompt, task_type="research")
        return {
            "squad_id": squad_id,
            "engine": "fallback-gemini",
            "status": "completed",
            "result": result,
            "agents_count": len(agents_list),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("Erro no fallback: %s", e)
        return {
            "squad_id": squad_id,
            "engine": "fallback-gemini",
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }


# ─── API Pública ────────────────────────────────────────────

async def run_squad(
    squad_id: str,
    task_description: str,
    force_engine: str | None = None,
) -> dict[str, object]:
    """
    Executa um squad autônomo.

    Args:
        squad_id: ID do squad (research, sales, content, code)
        task_description: Descrição da tarefa a executar
        force_engine: Forçar motor específico (crewai, swarm, fallback)

    Returns:
        Resultado da execução do squad
    """
    engine = force_engine or _get_engine()

    logger.info(
        "🐉 Squad Runner: squad='%s', engine='%s', task='%s'",
        squad_id,
        engine,
        task_description[:80],
    )

    if engine == "crewai":
        return await run_squad_crewai(squad_id, task_description)
    elif engine == "swarm":
        return await run_squad_swarm(squad_id, task_description)
    else:
        return await run_squad_fallback(squad_id, task_description)


def list_squads() -> list[dict[str, object]]:
    """Lista todos os squads disponíveis."""
    squads: list[dict[str, object]] = []
    for squad_id, config in SQUAD_CONFIGS.items():
        agents_list = config.get("agents", [])
        squads.append({
            "id": squad_id,
            "name": config.get("name", squad_id),
            "description": config.get("description", ""),
            "agents_count": len(agents_list) if isinstance(agents_list, list) else 0,
            "engine": _get_engine(),
        })
    return squads


def get_squad_info(squad_id: str) -> dict[str, object] | None:
    """Retorna informações detalhadas de um squad."""
    config = SQUAD_CONFIGS.get(squad_id)
    if not config:
        return None
    return {
        "id": squad_id,
        **config,
        "engine": _get_engine(),
    }
