"""
System Auditor — Gera relatório de saúde do KAIROS.
Conta scripts, RPs, squads, engine files, workers e integrações.
Usado pelo intent 'status' para dar uma visão completa ao Gabriel.
"""
import logging
from pathlib import Path

logger = logging.getLogger("kairos.auditor")

# Diretórios relativos à raiz do KAIROS (não do orchestrator)
KAIROS_ROOT = Path(__file__).parent.parent.parent  # My KAIROS/


def count_files(directory: str, extensions: list[str] | None = None) -> int:
    """Conta arquivos em um diretório (recursivo)."""
    target = KAIROS_ROOT / directory
    if not target.exists():
        return 0
    count = 0
    for f in target.rglob("*"):
        if f.is_file() and not any(p.startswith(".git") for p in f.parts):
            if extensions is None or f.suffix.lower() in extensions:
                count += 1
    return count


def get_system_health() -> dict:
    """Retorna métricas de saúde do sistema KAIROS."""
    return {
        "scripts": count_files("scripts", [".js", ".py", ".sh", ".ps1"]),
        "reasoning_packages": count_files("reasoning-packages", [".md"]),
        "squads": count_files("squads", [".yaml", ".yml", ".md"]),
        "engine": count_files("engine"),
        "workers": count_files("kairos-orchestrator/workers", [".py"]),
        "clients": count_files("clients"),
        "docs": count_files("docs"),
        "tools": len(list((KAIROS_ROOT / "tools").iterdir())) if (KAIROS_ROOT / "tools").exists() else 0,
    }


def format_health_report() -> str:
    """Formata relatório de saúde para exibição no Telegram."""
    health = get_system_health()
    total = sum(health.values())

    lines = [
        "🏥 *SAÚDE DO SISTEMA KAIROS*\n",
        f"📜 Scripts: {health['scripts']}",
        f"🧠 Reasoning Packages: {health['reasoning_packages']}",
        f"👥 Squads: {health['squads']}",
        f"⚙️ Engine: {health['engine']}",
        f"🔧 Workers: {health['workers']}",
        f"🏢 Clients (files): {health['clients']}",
        f"📚 Docs: {health['docs']}",
        f"🔗 Tools/Integrations: {health['tools']}",
        f"\n📊 *Total: {total} artefatos ativos*",
    ]

    # Calcular score de saúde
    score = 0
    if health["scripts"] > 50:
        score += 2
    if health["reasoning_packages"] > 40:
        score += 2
    if health["workers"] >= 5:
        score += 2
    if health["engine"] > 30:
        score += 2
    if health["clients"] > 100:
        score += 2

    bars = "█" * score + "░" * (10 - score)
    lines.append(f"\n💪 Health Score: [{bars}] {score}/10")

    return "\n".join(lines)
