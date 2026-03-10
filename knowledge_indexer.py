#!/usr/bin/env python3
"""
knowledge_indexer.py — Indexa TODOS os arquivos do KAIROS no Knowledge Brain (Supabase).

Este script escaneai o repositório KAIROS, lê cada arquivo relevante,
gera um resumo e divide em chunks para armazenamento no Supabase.
O KAIROS SKY usa esses chunks para responder perguntas com contexto total
sem precisar re-ler arquivos ou ser re-contextualizado.

USO:
    python knowledge_indexer.py                    # indexa tudo
    python knowledge_indexer.py --category rp      # só RPs
    python knowledge_indexer.py --force             # re-indexa mesmo sem mudanças
"""

import os
import sys
import hashlib
import argparse
import logging
from pathlib import Path

# Adicionar diretório pai ao path para importar config/supabase
sys.path.insert(0, str(Path(__file__).parent))

from supabase_client import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("kairos.indexer")

# Tamanho máximo de cada chunk (caracteres)
CHUNK_SIZE = 4000

# Diretórios e extensões para indexar
INDEX_CONFIG = {
    "rp": {
        "paths": ["reasoning-packages/"],
        "extensions": [".md"],
        "description": "Reasoning Packages — documentos estratégicos",
    },
    "docs": {
        "paths": ["docs/"],
        "extensions": [".md"],
        "description": "Documentação core do KAIROS",
    },
    "scripts": {
        "paths": ["scripts/"],
        "extensions": [".js", ".py", ".sh", ".ps1"],
        "description": "Scripts operacionais do KAIROS",
    },
    "agents": {
        "paths": [".agent/", ".antigravity/", "squads/"],
        "extensions": [".md", ".json"],
        "description": "Configuração de agentes e squads",
    },
    "clients": {
        "paths": ["clients/"],
        "extensions": [".md", ".json", ".css", ".html"],
        "description": "Projetos de clientes (Experia, Hortifruti, Master Pumps)",
    },
    "config": {
        "paths": ["./"],
        "extensions": [".md", ".json"],
        "description": "Arquivos de configuração raiz",
        "max_depth": 1,
    },
    "workflows": {
        "paths": [".agent/workflows/"],
        "extensions": [".md"],
        "description": "Workflows de ativação de agentes",
    },
}

# Arquivos/diretórios para IGNORAR
IGNORE_PATTERNS = {
    "node_modules", ".git", ".aios-core", "package-lock.json",
    "bun.lockb", ".env", "apex-conductor-main", ".gemini",
    "temp-mp-deploy", "releases", "logs",
}

# Arquivos-chave que DEVEM ter tag "core"
CORE_FILES = {
    "KAIROS-MANIFEST.md", "KAIROS_ENGINEERING_BIBLE.md",
    "KAIROS_ENGINEERING_BIBLE_v2.md", "RP-GABRIEL-OS-CONSOLIDATED-v3.0.md",
    "GABRIEL-ANAMNESIS-GENIALIDADE.md", "INSTRUCAO-ATIVACAO-KAIROS-v1.0.md",
    "README.md", "AGENTS.md",
}


def compute_hash(content: str) -> str:
    """Calcula hash SHA256 do conteúdo."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def generate_summary(file_path: str, content: str) -> str:
    """Gera resumo baseado no conteúdo (sem IA — heurístico rápido)."""
    lines = content.strip().split("\n")

    # Pegar primeiros headers ou linhas não-vazias
    summary_parts = []
    for line in lines[:30]:
        stripped = line.strip()
        if stripped.startswith("#"):
            summary_parts.append(stripped.lstrip("#").strip())
        elif stripped and not stripped.startswith("```") and not stripped.startswith("---"):
            summary_parts.append(stripped[:200])
        if len(summary_parts) >= 5:
            break

    if summary_parts:
        return " | ".join(summary_parts)[:500]
    return f"Arquivo: {os.path.basename(file_path)}"


def auto_tag(file_path: str, content: str) -> list:
    """Gera tags automaticamente baseado no path e conteúdo."""
    tags = []
    path_lower = file_path.lower().replace("\\", "/")
    name = os.path.basename(file_path)

    # Tags por diretório
    if "reasoning-packages" in path_lower:
        tags.append("rp")
    if "strategic" in path_lower:
        tags.append("strategic")
    if "core" in path_lower:
        tags.append("core")
    if "clients/" in path_lower:
        tags.append("client")
    if "experia" in path_lower:
        tags.append("experia")
    if "squads/" in path_lower:
        tags.append("squad")
    if "workflows/" in path_lower:
        tags.append("workflow")
    if "scripts/" in path_lower:
        tags.append("script")
    if "docs/" in path_lower:
        tags.append("docs")

    # Tags por conteúdo
    content_lower = content.lower()
    if "gabriel" in content_lower:
        tags.append("gabriel")
    if "experia" in content_lower:
        tags.append("experia")
    if "pareto" in content_lower:
        tags.append("pareto")
    if "kairos" in content_lower:
        tags.append("kairos")

    # Core files
    if name in CORE_FILES:
        tags.append("core")
        tags.append("priority")

    return list(set(tags))


def chunk_content(content: str) -> list:
    """Divide conteúdo em chunks de CHUNK_SIZE caracteres."""
    if len(content) <= CHUNK_SIZE:
        return [content]

    chunks = []
    lines = content.split("\n")
    current_chunk = ""

    for line in lines:
        if len(current_chunk) + len(line) + 1 > CHUNK_SIZE:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = line
        else:
            current_chunk += ("\n" if current_chunk else "") + line

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def should_ignore(path: str) -> bool:
    """Verifica se o path deve ser ignorado."""
    parts = Path(path).parts
    for part in parts:
        if part in IGNORE_PATTERNS:
            return True
    return False


def scan_files(root: str, category: str | None = None) -> list:
    """Escaneia e retorna lista de arquivos para indexar."""
    files = []
    categories = INDEX_CONFIG if not category else {category: INDEX_CONFIG.get(category, {})}

    for cat_name, config in categories.items():
        if not config:
            continue
        max_depth = config.get("max_depth", 10)
        for base_path in config["paths"]:
            full_path = os.path.join(root, base_path)
            if not os.path.exists(full_path):
                continue

            for dirpath, dirnames, filenames in os.walk(full_path):
                # Respeitar max_depth
                depth = len(Path(dirpath).relative_to(full_path).parts)
                if depth > max_depth:
                    dirnames.clear()
                    continue

                # Filtrar diretórios ignorados
                dirnames[:] = [d for d in dirnames if d not in IGNORE_PATTERNS]

                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in config["extensions"] and not should_ignore(filepath):
                        rel_path = os.path.relpath(filepath, root)
                        files.append({
                            "abs_path": filepath,
                            "rel_path": rel_path.replace("\\", "/"),
                            "name": filename,
                            "category": cat_name,
                        })

    return files


def index_file(client, file_info: dict, force: bool = False) -> int:
    """Indexa um arquivo no Knowledge Brain. Retorna número de chunks."""
    try:
        with open(file_info["abs_path"], "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        logger.warning("Não conseguiu ler %s: %s", file_info["rel_path"], e)
        return 0

    if not content.strip():
        return 0

    content_hash = compute_hash(content)
    file_size = len(content.encode("utf-8"))

    # Verificar se já indexado (pelo hash)
    if not force:
        existing = client.table("knowledge_brain").select("content_hash").eq(
            "file_path", file_info["rel_path"]
        ).eq("chunk_index", 0).execute()
        if existing.data and existing.data[0].get("content_hash") == content_hash:
            logger.debug("Sem alteração: %s", file_info["rel_path"])
            return 0

    # Gerar metadados
    summary = generate_summary(file_info["rel_path"], content)
    tags = auto_tag(file_info["rel_path"], content)
    chunks = chunk_content(content)

    # Deletar registros antigos deste arquivo
    client.table("knowledge_brain").delete().eq("file_path", file_info["rel_path"]).execute()

    # Inserir chunks
    records = []
    for i, chunk in enumerate(chunks):
        records.append({
            "file_path": file_info["rel_path"],
            "file_name": file_info["name"],
            "category": file_info["category"],
            "summary": summary,
            "content_hash": content_hash,
            "file_size": file_size,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "content_chunk": chunk,
            "tags": tags,
        })

    # Inserir em batch (máximo 50 por vez)
    for i in range(0, len(records), 50):
        batch = records[i:i+50]
        client.table("knowledge_brain").insert(batch).execute()

    logger.info("✅ %s → %d chunks [%s]", file_info["rel_path"], len(chunks), ", ".join(tags))
    return len(chunks)


def main():
    parser = argparse.ArgumentParser(description="KAIROS Knowledge Brain Indexer")
    parser.add_argument("--category", "-c", help="Categoria para indexar (rp, docs, scripts, agents, clients, config, workflows)")
    parser.add_argument("--force", "-f", action="store_true", help="Re-indexar mesmo sem mudanças")
    args = parser.parse_args()

    # Determinar raiz do KAIROS
    root = str(Path(__file__).parent.parent)
    logger.info("═" * 50)
    logger.info("  🧠 KAIROS Knowledge Brain Indexer")
    logger.info("  Raiz: %s", root)
    logger.info("═" * 50)

    # Escanear arquivos
    files = scan_files(root, args.category)
    logger.info("Encontrados: %d arquivos para indexar", len(files))

    if not files:
        logger.warning("Nenhum arquivo encontrado!")
        return

    # Conectar Supabase
    client = get_client()

    # Indexar
    total_chunks = 0
    indexed = 0
    for file_info in files:
        chunks = index_file(client, file_info, args.force)
        total_chunks += chunks
        if chunks > 0:
            indexed += 1

    logger.info("═" * 50)
    logger.info("  Resultado: %d/%d arquivos indexados, %d chunks totais", indexed, len(files), total_chunks)
    logger.info("═" * 50)


if __name__ == "__main__":
    main()
