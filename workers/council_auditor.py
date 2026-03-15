"""
IA Council Light — Auditoria e Auto-evolução.

Adaptado do RP-20260218-EVOLUTION-ENGINE:
Versão Python do `ia-council-engine.js`.
Originalmente 7 cadeiras. Para o SKY (Cloud MVP), mantemos as 3 essenciais:
  1. Code Quality & Architect (Uncle Bob/Linus) -> foco em estabilidade e Python
  2. Workflow & Efficiency (Tim Ferriss/Clear) -> foco na Gabriel OS e Pareto
  3. Product & Client (Hormozi/Jobs) -> foco na Experia e R$ 30K/mês

Roda via night_processor ou task separada. Avalia o sistema e propõe gaps.
"""
import logging
from typing import TypedDict
from datetime import date

import supabase_client as db
from workers.task_worker import call_model


logger = logging.getLogger("kairos.council")


class CouncilVerdict(TypedDict, total=False):
    """Veredito estruturado do IA Council."""
    cadeira: str
    gap_encontrado: str
    solucao_proposta: str
    prioridade: int # 1-10


PROMPT_COUNCIL = """
O Conclave KAIROS foi convocado. Vocês são 3 mentes geniais avaliando o estado atual de Gabriel e do sistema SKY.

CONTEXTO ATUAL (Métricas e Memórias):
{system_context}

AVALIAÇÕES REQUERIDAS:
1. Cadeira de Arquitetura & Código: Avalie a estabilidade, organização e performance do sistema KAIROS.
2. Cadeira de Workflow & Pareto: Avalie os blocos de tempo, foco na Zona Sagrada 🔵 e vazamentos de energia.
3. Cadeira de Produto & Receita: Avalie o pipeline da Experia, a meta de R$ 30K MRR e o foco no ICP.

REGRAS:
Sejam diretos e brutais. Se Gabriel está focando no 99% inutil ao invés do 1% crucial, digam.
Retornem APENAS um bloco JSON válido (sem marcação markdown). As chaves devem ser as 3 cadeiras. Cada uma com "gap_encontrado", "solucao_proposta", "prioridade" (int 1-10) e "explicacao".

Exemplo JSON:
{
  "Arquitetura": {"gap_encontrado": "...", "solucao_proposta": "...", "prioridade": 8, "explicacao": "..."},
  "Workflow": {"gap_encontrado": "...", "solucao_proposta": "...", "prioridade": 9, "explicacao": "..."},
  "Produto": {"gap_encontrado": "...", "solucao_proposta": "...", "prioridade": 10, "explicacao": "..."}
}
"""


def convene_council() -> str:
    """
    Convoca o Council para auditar o contexto atual.
    Retorna o relatório formatado.
    """
    logger.info("🏛️ Convocando IA Council (3 cadeiras)")
    
    try:
        from workers.cognitive_state import get_state_summary
        from workers.learning_model import get_insights_for_brief
        from workers.context_sync import get_system_status
        
        ctx_parts = [
            "--- SYSTEM STATUS ---",
            get_system_status(),
            "\n--- COGNITIVE STATE ---",
            get_state_summary(),
            "\n--- LEARNING MODEL ---",
            get_insights_for_brief(),
        ]
        
        # Arsenal de ferramentas disponíveis
        try:
            from workers.tools_registry import get_conclave_context
            ctx_parts.append("\n--- ARSENAL ---")
            ctx_parts.append(get_conclave_context())
        except Exception:
            pass

        ctx_parts.append("\n--- RECENT MEMORIES ---")
        recent = db.get_recent_memories(limit=10)
        for m in recent:
            ctx_parts.append(f"- {m.get('content_chunk', '')}")
            
        system_context = "\n".join(ctx_parts)
    except Exception as e:
        logger.warning("Falha ao montar contexto para o Council: %s", e)
        system_context = "Contexto indisponível."

    prompt = PROMPT_COUNCIL.format(system_context=system_context[:10000])  # Limit to avoid huge context window
    
    raw_answer = call_model(prompt, category="gemini-high", title="IA Council")
    
    try:
        # Clean JSON
        json_str = raw_answer.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        elif json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()
        
        import json
        verdicts = json.loads(json_str)
        
        report_lines = ["🏛️ VEREDITO DO IA COUNCIL"]
        
        for cadeira, detalhes in verdicts.items():
            report_lines.append(f"\n[{cadeira}] (Prioridade: {detalhes.get('prioridade', '?')}/10)")
            report_lines.append(f"⚠️ GAP: {detalhes.get('gap_encontrado', '')}")
            report_lines.append(f"💡 SOLUÇÃO: {detalhes.get('solucao_proposta', '')}")
            report_lines.append(f"📝 {detalhes.get('explicacao', '')}")
            
            # Adicionar como task se prioridade >= 8
            if int(detalhes.get("prioridade", 0)) >= 8:
                db.add_task(
                    title=f"Council: {detalhes.get('gap_encontrado', '')}",
                    category="council_directive",
                    priority=detalhes.get("prioridade", 8),
                    input_data={"cadeira": cadeira, "solucao": detalhes.get('solucao_proposta', '')},
                    created_by="ia_council"
                )
        
        final_report = "\n".join(report_lines)
        db.log_memory("ia_council_verdict", final_report)
        logger.info("Council concluído com sucesso.")
        return final_report

    except Exception as e:
        logger.error("Falha ao processar veredito do Council: %s\n%s", e, raw_answer)
        return f"Falha ao rodar IA Council. Raw output:\n{raw_answer}"
