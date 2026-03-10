# Model Router — escolhe modelo certo por tipo de task
import logging
from config import ROUTING_RULES, ROUTING_KEYWORDS, DEFAULT_MODEL

logger = logging.getLogger("kairos.router")


def route_model(category: str = "", title: str = "") -> str:
    """Determina qual modelo usar baseado na categoria e título da task."""

    # 1. Verificar por categoria direta
    if category in ROUTING_RULES:
        model = ROUTING_RULES[category]
        logger.info("Roteado por categoria '%s' → %s", category, model)
        return model

    # 2. Verificar por keywords no título
    title_lower = title.lower()
    for model, keywords in ROUTING_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title_lower:
                logger.info("Roteado por keyword '%s' → %s", keyword, model)
                return model

    # 3. Default
    logger.info("Sem match — usando default: %s", DEFAULT_MODEL)
    return DEFAULT_MODEL
