"""
Learning Model — Meta-aprendizado sobre Gabriel.

Do RP-20260218-OPERATOR-NOESIS:
  Não aprende mais SOBRE Gabriel. Aprende COMO aprender sobre Gabriel.
  O modelo de conhecimento do operador evolui com o tempo.

Conceitos-chave:
  → Source weights: quais fontes de dados sobre Gabriel são mais preditivas
  → Inference patterns: padrões comportamentais observados + validados
  → Predictions: apostas falsificáveis sobre comportamento futuro
  → Model accuracy: taxa de acerto para medir se está aprendendo

Seed dos 18 padrões da Anamnesis de Gabriel.
"""
import json
import logging
from datetime import datetime, date
from typing import TypedDict

import supabase_client as db


logger = logging.getLogger("kairos.learning")

CATEGORY = "learning_model"
MAX_ACTIVE_PREDICTIONS = 5


# ─── Types ─────────────────────────────────────────────────

class InferencePattern(TypedDict, total=False):
    """Padrão inferido sobre o comportamento de Gabriel."""
    pattern_id: str
    description: str
    confidence: float  # 0.0 a 1.0
    evidence_count: int
    first_observed: str
    last_validated: str


class Prediction(TypedDict, total=False):
    """Predição falsificável sobre Gabriel."""
    prediction_id: str
    made_on: str
    behavior: str
    timeframe: str
    confidence: float
    outcome: str | None  # confirmed | refuted | inconclusive | None


class LearningModel(TypedDict, total=False):
    """Modelo completo de aprendizado sobre Gabriel."""
    operator_id: str
    model_version: int
    last_updated: str
    source_weights: dict[str, float]
    inference_patterns: list[InferencePattern]
    active_predictions: list[Prediction]
    prediction_log: list[Prediction]
    model_accuracy: dict[str, object]


# ─── Seed do Modelo (Anamnesis de Gabriel) ─────────────────

SEED_PATTERNS: list[InferencePattern] = [
    {
        "pattern_id": "delay-reveals-priority",
        "description": "O que Gabriel adia por >2 sessões é prioridade real mascarada por bloqueio.",
        "confidence": 0.78,
        "evidence_count": 12,
        "first_observed": "anamnesis",
        "last_validated": "anamnesis",
    },
    {
        "pattern_id": "novelty-is-fuel",
        "description": "Gabriel tem energia máxima quando o tema é novo. Repetição mata engajamento.",
        "confidence": 0.85,
        "evidence_count": 18,
        "first_observed": "anamnesis",
        "last_validated": "anamnesis",
    },
    {
        "pattern_id": "architect-not-operator",
        "description": "Gabriel entra em flow quando CRIA, sai dele quando tem que OPERAR o criado.",
        "confidence": 0.82,
        "evidence_count": 15,
        "first_observed": "anamnesis",
        "last_validated": "anamnesis",
    },
    {
        "pattern_id": "voice-is-superpower",
        "description": "A Voz é o superpower de Gabriel (herdada da mãe). Comunicação é vetor natural.",
        "confidence": 0.90,
        "evidence_count": 20,
        "first_observed": "anamnesis",
        "last_validated": "anamnesis",
    },
    {
        "pattern_id": "procrastination-inversely-proportional",
        "description": "Quanto MAIOR o impacto da tarefa, MAIOR o adiamento. O tamanho do bloqueio revela o tamanho da oportunidade.",
        "confidence": 0.75,
        "evidence_count": 10,
        "first_observed": "anamnesis",
        "last_validated": "anamnesis",
    },
]

INITIAL_SOURCE_WEIGHTS: dict[str, float] = {
    "declarative": 0.25,   # o que Gabriel diz
    "behavioral": 0.45,    # o que Gabriel faz
    "decisional": 0.20,    # o que Gabriel escolhe
    "omission": 0.10,      # o que Gabriel não diz
}


# ─── Funções Públicas ──────────────────────────────────────

def initialize_model() -> LearningModel:
    """
    Cria o modelo de aprendizado inicial com seed da Anamnesis.
    Chamado uma vez quando o modelo não existe.
    """
    model: LearningModel = {
        "operator_id": "gabriel",
        "model_version": 1,
        "last_updated": datetime.now().isoformat(),
        "source_weights": INITIAL_SOURCE_WEIGHTS.copy(),
        "inference_patterns": list(SEED_PATTERNS),
        "active_predictions": [],
        "prediction_log": [],
        "model_accuracy": {
            "predictions_made": 0,
            "confirmed": 0,
            "refuted": 0,
            "accuracy_rate": 0.0,
            "trend": "new",
        },
    }
    _save_model(model)
    logger.info("🧬 Learning Model inicializado com %d padrões seed da Anamnesis", len(SEED_PATTERNS))
    return model


def get_model() -> LearningModel:
    """Retorna o modelo atual ou inicializa um novo."""
    try:
        client = db.get_client()
        response = (
            client.table("knowledge_brain")
            .select("content_chunk")
            .eq("category", CATEGORY)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            raw = response.data[0].get("content_chunk", "{}")
            parsed = json.loads(raw)
            model: LearningModel = {
                "operator_id": parsed.get("operator_id", "gabriel"),
                "model_version": parsed.get("model_version", 1),
                "last_updated": parsed.get("last_updated", ""),
                "source_weights": parsed.get("source_weights", INITIAL_SOURCE_WEIGHTS.copy()),
                "inference_patterns": parsed.get("inference_patterns", []),
                "active_predictions": parsed.get("active_predictions", []),
                "prediction_log": parsed.get("prediction_log", []),
                "model_accuracy": parsed.get("model_accuracy", {}),
            }
            return model
    except Exception as e:
        logger.error("Erro ao carregar modelo: %s. Inicializando novo.", e)
    return initialize_model()


def add_prediction(
    behavior: str,
    timeframe: str = "próximas 3 sessões",
    confidence: float = 0.50,
) -> bool:
    """
    Adiciona uma predição falsificável sobre Gabriel.
    Max 5 ativas simultâneas (RULE do RP).
    """
    model = get_model()
    active = model.get("active_predictions", [])
    if len(active) >= MAX_ACTIVE_PREDICTIONS:
        logger.warning("Máximo de %d predições ativas atingido. Remova ou valide uma.", MAX_ACTIVE_PREDICTIONS)
        return False

    prediction: Prediction = {
        "prediction_id": f"pred-{len(model.get('prediction_log', [])) + 1:03d}",
        "made_on": date.today().isoformat(),
        "behavior": behavior,
        "timeframe": timeframe,
        "confidence": confidence,
        "outcome": None,
    }
    active.append(prediction)
    model["active_predictions"] = active
    _save_model(model)
    logger.info("🔮 Predição adicionada: %s (confidence: %.0f%%)", behavior[:60], confidence * 100)
    return True


def validate_prediction(prediction_id: str, outcome: str) -> bool:
    """
    Valida uma predição (confirmed | refuted | inconclusive).
    Atualiza model_accuracy e ajusta source_weights.
    """
    if outcome not in ("confirmed", "refuted", "inconclusive"):
        logger.error("Outcome inválido: %s. Use confirmed/refuted/inconclusive.", outcome)
        return False

    model = get_model()
    active = model.get("active_predictions", [])
    target = None
    remaining: list[Prediction] = []

    for pred in active:
        if pred.get("prediction_id") == prediction_id:
            target = pred
        else:
            remaining.append(pred)

    if not target:
        logger.warning("Predição %s não encontrada entre as ativas.", prediction_id)
        return False

    # Registrar resultado
    target["outcome"] = outcome
    model.get("prediction_log", []).append(target)
    model["active_predictions"] = remaining

    # Atualizar accuracy
    accuracy = model.get("model_accuracy", {})
    total = int(accuracy.get("predictions_made", 0)) + 1
    confirmed = int(accuracy.get("confirmed", 0))
    refuted = int(accuracy.get("refuted", 0))

    if outcome == "confirmed":
        confirmed += 1
    elif outcome == "refuted":
        refuted += 1

    accuracy["predictions_made"] = total
    accuracy["confirmed"] = confirmed
    accuracy["refuted"] = refuted
    accuracy["accuracy_rate"] = round(confirmed / total, 2) if total > 0 else 0.0
    accuracy["trend"] = _calculate_trend(model.get("prediction_log", []))
    model["model_accuracy"] = accuracy

    # Ajustar source weights se temos dados suficientes
    if total >= 5:
        _adjust_source_weights(model, outcome)

    _save_model(model)

    emoji = "✅" if outcome == "confirmed" else "❌" if outcome == "refuted" else "⚪"
    logger.info(
        "%s Predição %s: %s | Accuracy: %.0f%% (%s)",
        emoji, prediction_id, outcome, accuracy["accuracy_rate"] * 100, accuracy["trend"],
    )
    return True


def get_insights_for_brief() -> str:
    """
    Gera insights do Learning Model para injeção no morning brief.
    Mostra padrões de alta confiança + predições ativas.
    """
    model = get_model()
    lines: list[str] = ["🧬 LEARNING MODEL:"]

    # Padrões de alta confiança
    patterns = model.get("inference_patterns", [])
    high_confidence = [p for p in patterns if p.get("confidence", 0) >= 0.75]
    if high_confidence:
        lines.append(f"  📊 {len(high_confidence)} padrão(ões) estabelecido(s):")
        for p in high_confidence[:3]:
            lines.append(f"    → {p['description'][:80]} ({p['confidence']:.0%})")

    # Predições ativas
    active = model.get("active_predictions", [])
    if active:
        lines.append(f"  🔮 {len(active)} predição(ões) em observação:")
        for pred in active:
            lines.append(f"    → {pred['behavior'][:70]} [{pred['timeframe']}]")

    # Accuracy
    accuracy = model.get("model_accuracy", {})
    rate = accuracy.get("accuracy_rate", 0)
    total = accuracy.get("predictions_made", 0)
    if total > 0:
        lines.append(f"  📈 Precisão: {rate:.0%} ({total} predições | trend: {accuracy.get('trend', '?')})")

    # Source weights
    weights = model.get("source_weights", {})
    if weights:
        top_source = max(weights, key=lambda k: weights[k])
        lines.append(f"  ⚖️ Fonte mais preditiva: {top_source} ({weights[top_source]:.0%})")

    return "\n".join(lines)


def get_pattern_by_id(pattern_id: str) -> InferencePattern | None:
    """Busca um padrão de inferência pelo ID."""
    model = get_model()
    for pattern in model.get("inference_patterns", []):
        if pattern.get("pattern_id") == pattern_id:
            return pattern
    return None


def register_evidence(pattern_id: str, confirmed: bool = True) -> bool:
    """
    Registra evidência para/contra um padrão.
    Ajusta confidence: +3% se confirmado, -2% se refutado.
    """
    model = get_model()
    for pattern in model.get("inference_patterns", []):
        if pattern.get("pattern_id") == pattern_id:
            delta = 0.03 if confirmed else -0.02
            new_conf = max(0.1, min(0.99, pattern.get("confidence", 0.5) + delta))
            pattern["confidence"] = round(new_conf, 2)
            pattern["evidence_count"] = pattern.get("evidence_count", 0) + 1
            pattern["last_validated"] = date.today().isoformat()
            _save_model(model)
            logger.info(
                "📊 Evidência para %s: %s → confidence: %.0f%%",
                pattern_id, "✅" if confirmed else "❌", new_conf * 100,
            )
            return True
    logger.warning("Padrão %s não encontrado.", pattern_id)
    return False


# ─── Funções Privadas ──────────────────────────────────────

def _save_model(model: LearningModel) -> None:
    """Salva o modelo no knowledge_brain."""
    model["last_updated"] = datetime.now().isoformat()
    content = json.dumps(model, ensure_ascii=False, indent=2)
    db.save_memory(
        content=content,
        category=CATEGORY,
        tags=["learning_model", "gabriel", date.today().isoformat()],
        source="noesis",
    )


def _calculate_trend(prediction_log: list[Prediction]) -> str:
    """Calcula tendência baseada nas últimas 10 predições."""
    if len(prediction_log) < 5:
        return "insufficient_data"

    recent = prediction_log[-10:]
    first_half = recent[: len(recent) // 2]
    second_half = recent[len(recent) // 2:]

    def accuracy(preds: list[Prediction]) -> float:
        confirmed = sum(1 for p in preds if p.get("outcome") == "confirmed")
        total = sum(1 for p in preds if p.get("outcome") in ("confirmed", "refuted"))
        return confirmed / total if total > 0 else 0.0

    a1 = accuracy(first_half)
    a2 = accuracy(second_half)

    if a2 > a1 + 0.05:
        return "improving"
    if a2 < a1 - 0.05:
        return "declining"
    return "stable"


def _adjust_source_weights(model: LearningModel, last_outcome: str) -> None:
    """
    Ajusta pesos das fontes baseado em resultados.
    Micro-ajustes: +2% confirmada, -1% refutada. Normaliza.
    """
    weights = model.get("source_weights", INITIAL_SOURCE_WEIGHTS.copy())

    # Ajuste simples: se confirmou, reforça behavioral (maior peso initial)
    # Refinamento futuro: rastrear qual fonte gerou qual predição
    primary = "behavioral"
    if last_outcome == "confirmed":
        weights[primary] = min(0.60, weights.get(primary, 0.45) + 0.02)
    elif last_outcome == "refuted":
        weights[primary] = max(0.10, weights.get(primary, 0.45) - 0.01)

    # Normalizar para soma = 1.0
    total = sum(weights.values())
    if total > 0:
        for key in weights:
            weights[key] = round(weights[key] / total, 2)

    model["source_weights"] = weights
