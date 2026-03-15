"""
Jarvis Pipeline — Absorção 3-Prompts.

Do RP-20260227-MEGABRAIN-JARVIS-PIPELINE:
O "Projeto Híbrido Jarvis" do Thiago Finch usa um pipeline de 3 prompts:
1. Index (Chunking + Entity Resolution)
2. Insight Extraction (com prioridades)
3. Strategic Narrative Synthesis

Este worker processa textos longos / transcripts / batches de chat
através das 3 camadas e salva no Knowledge Brain (como memórias e narrativas).
"""
import json
import logging
from datetime import date
from typing import TypedDict

import supabase_client as db
from workers.task_worker import call_model
from workers.narrative_builder import update_narrative


logger = logging.getLogger("kairos.jarvis_pipeline")


class BaseInsight(TypedDict, total=False):
    """Insight model do Prompt 2."""
    entity: str
    insight: str
    priority: str  # high|medium|low
    category: str  # pessoa|tema


# ─── Prompts do Pipeline ───────────────────────────────────

PROMPT_1_INDEX = """
Você é o Indexador Jarvis Nível 1.
Seu objetivo é extrair entidades importantes (Pessoas, Empresas, Projetos) 
e identificar os blocos de informação cruciais (chunks) do texto fornecido.

1. Identifique os participantes (Speakers/Entities).
2. Para cada Ponto Chave discutido, descreva o que foi dito de forma concisa.
3. Se houver nomes, aplique Entity Resolution (Gabi/Gabriel -> Gabriel, etc).

Formato de saída (JSON Restrito):
{
  "entities_found": ["Nome 1", "Nome 2"],
  "chunks": [
    {
      "topic": "Tema",
      "entities_involved": ["Nome 1"],
      "content": "Resumo do que foi dito"
    }
  ]
}

Texto a processar:
{text_input}
"""

PROMPT_2_INSIGHT = """
Você é o Extrator Jarvis Nível 2.
Baseado nos chunks de informação abaixo, você deve extrair INSIGHTS acionáveis ou de longo prazo.
Para cada insight, atribua uma Prioridade (high, medium, low) e identifique a Entidade principal.

Definição de High: Bloqueios, dívidas, promessas, decisões críticas, vulnerabilidades.
Definição de Medium: Dados de contexto, evolução de um projeto, preferência de longo prazo.
Definição de Low: Comentários pontuais sem peso estrutural.

Formato de saída (JSON Restrito):
{
  "insights": [
    {
      "entity": "Nome da Pessoa ou Projeto",
      "insight": "O que de fato importa sobre ela neste contexto.",
      "priority": "high",
      "category": "pessoa"
    }
  ]
}

Chunks:
{chunks_json}
"""


# ─── Pipeline Core ─────────────────────────────────────────

def process_text_batch(raw_text: str, source: str = "batch") -> dict[str, object]:
    """
    Executa a transcrição ou blocos de texto por ambos Prompt 1 e Prompt 2,
    salvando os insights e repassando para a camada de narrativas (Prompt 3).
    """
    logger.info("📡 Iniciando Jarvis Pipeline para entrada: %d chars", len(raw_text))
    
    # [CAMADA 1] Canonicalização e Extração
    p1_enriched = PROMPT_1_INDEX.format(text_input=raw_text)
    p1_raw_answer = call_model(p1_enriched, category="gemini-flash", title="Jarvis L1")
    
    try:
        # Tentar extrair o JSON
        json_str = _clean_json(p1_raw_answer)
        l1_data = json.loads(json_str)
        entities = l1_data.get("entities_found", [])
        chunks = l1_data.get("chunks", [])
        
        # Registrar novos aliases on-the-fly se óbvio (simplificado via normalize_entity local)
        normalized_chunks = []
        for c in chunks:
            ents = [db.normalize_entity(e) for e in c.get("entities_involved", [])]
            c["entities_involved"] = ents
            normalized_chunks.append(c)
            
        logger.info("L1 concluído: %d chunks encontrados. Entities: %s", len(normalized_chunks), entities)
        
    except json.JSONDecodeError as e:
        logger.error("Falha no parse L1: %s\n%s", e, p1_raw_answer)
        return {"status": "error", "step": "L1", "reason": "invalid_json"}
        
    # [CAMADA 2] Insight Extraction
    if not normalized_chunks:
        return {"status": "success", "insights": 0, "message": "Nenhum chunk relevante"}
        
    p2_enriched = PROMPT_2_INSIGHT.format(chunks_json=json.dumps(normalized_chunks, ensure_ascii=False))
    p2_raw_answer = call_model(p2_enriched, category="gemini-flash", title="Jarvis L2")
    
    try:
        json_str2 = _clean_json(p2_raw_answer)
        l2_data = json.loads(json_str2)
        insights: list[BaseInsight] = l2_data.get("insights", [])
        
        # Filtrar e salvar os insights no memory index (Knowledge Brain)
        saved_insights = 0
        for item in insights:
            entity = item.get("entity", "unknown")
            insight_text = item.get("insight", "")
            priority = item.get("priority", "low")
            
            # Não salvar coisas low-priority na base pesada
            tags = ["jarvis-pipeline", entity, f"priority-{priority}", date.today().isoformat()]
            db.save_memory(
                content=f"[{entity}] {insight_text}",
                category="jarvis_insight",
                tags=tags,
                source=source,
            )
            saved_insights += 1
            
            # [CAMADA 3] Narrative Synthesis (Trigger)
            # Aciona a atualização assíncrona/desacoplada da biografia viva da entidade
            if priority in ("high", "medium"):
                update_narrative(entity, insight_text)
            
        logger.info("L2/L3 concluído: %d insights extraídos/salvos.", saved_insights)
        return {"status": "success", "chunks_processed": len(normalized_chunks), "insights": saved_insights}
        
    except json.JSONDecodeError as e:
        logger.error("Falha no parse L2: %s\n%s", e, p2_raw_answer)
        return {"status": "error", "step": "L2", "reason": "invalid_json"}


def _clean_json(raw: str) -> str:
    """Remove blocos markdown do texto do LLM para evitar erro de parse."""
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    return raw.strip()
