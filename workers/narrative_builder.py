"""
Narrative Builder (Narrativas Vivas) — Prompt 3 do Jarvis Pipeline.

Do RP-20260227-MEGABRAIN-JARVIS-PIPELINE (Camada 3):
Mantém um perfil progressivo de cada entidade (pessoa/projeto/empresa).
Atualiza a narrativa com novos insights sem perder o histórico do passado.

Salvo no Knowledge Brain com category="narrative".
"""
import logging
from datetime import date
from typing import TypedDict

import supabase_client as db
from workers.task_worker import call_model


logger = logging.getLogger("kairos.narrative_builder")


class Narrative(TypedDict, total=False):
    """Estrutura da Narrativa Viva."""
    entity: str
    last_updated: str
    insight_count: int
    content: str


PROMPT_3_NARRATIVE = """
Você é o Revisor Biográfico Jarvis Nível 3.
Sua missão é atualizar a "Narrativa Viva" da entidade [{entity}].

Instruções:
1. Analise o Perfil Mestre atual.
2. Incorpore os Novos Insights de forma fluida.
3. Não delete informações passadas, mas atualize os estados (ex: se um problema foi resolvido, marque como histórico).
4. Organize com títulos claros (Visão Geral, Pontos Focais Atuais, Histórico/Contexto).
5. O tom deve ser direto, objetivo e focado em inteligência de negócios/relacionamento.

--- PERFIL MESTRE ATUAL ---
{current_narrative}
---------------------------

--- NOVOS INSIGHTS A INCORPORAR ---
{new_insights}
-----------------------------------

Responda APENAS com a narrativa atualizada em Markdown.
"""


def get_narrative(entity: str) -> Narrative | None:
    """Recupera a narrativa atual de uma entidade."""
    normalized = db.normalize_entity(entity)
    query = f"narrative-{normalized.lower()}"
    
    # Buscar direto pelo file_name
    client = db.get_client()
    resp = client.table("knowledge_brain").select("*").eq("category", "narrative").eq("file_name", query).execute()
    
    if resp.data:
        record = resp.data[0]
        return Narrative(
            entity=normalized,
            last_updated=str(record.get("updated_at", "")),  # Pode não ser exato
            insight_count=1, # Aproximado, para uso local se precisar
            content=record.get("content_chunk", ""),
        )
    return None


def update_narrative(entity: str, new_insight: str) -> bool:
    """
    Atualiza (ou cria) a narrativa viva para uma entidade com um novo insight.
    """
    normalized = db.normalize_entity(entity)
    logger.info("✍️ Atualizando narrativa viva para: %s", normalized)
    
    current = get_narrative(normalized)
    current_content = current["content"] if current else f"# Perfil: {normalized}\n\nSem informações anteriores."
    
    prompt = PROMPT_3_NARRATIVE.format(
        entity=normalized,
        current_narrative=current_content,
        new_insights=f"- {new_insight}\n",
    )
    
    # Usar high model para capacidade de síntese
    new_content = call_model(prompt, category="gemini-high", title=f"Narrative {normalized}")
    
    # Salvar de volta
    file_name = f"narrative-{normalized.lower()}"
    file_path = f"jarvis://narrative/{normalized.lower()}"
    
    # Tentar upsert (mas save_memory não faz upsert diretamente, ele reinsere).
    # Melhor: buscar o ID e atualizar, ou deletar o antigo e criar novo.
    client = db.get_client()
    existing = client.table("knowledge_brain").select("id").eq("category", "narrative").eq("file_name", file_name).execute()
    
    if existing.data:
        # Update
        row_id = existing.data[0]["id"]
        client.table("knowledge_brain").update({
            "content_chunk": new_content,
            "summary": new_content[:100],
            "file_size": len(new_content.encode()),
            "tags": ["narrative", normalized, date.today().isoformat()],
        }).eq("id", row_id).execute()
    else:
        # Insert
        client.table("knowledge_brain").insert({
            "file_path": file_path,
            "file_name": file_name,
            "category": "narrative",
            "summary": new_content[:100],
            "content_chunk": new_content,
            "tags": ["narrative", normalized, date.today().isoformat()],
            "chunk_index": 0,
            "total_chunks": 1,
            "file_size": len(new_content.encode()),
            "content_hash": "", # Placeholder, não estritamente necessário para update manual
        }).execute()
        
    logger.info("✅ Narrativa viva atualizada para: %s", normalized)
    return True
