# Key Rotator — rotaciona API keys quando limite atingido
import logging
import time
from datetime import date
from config import GOOGLE_API_KEYS, GROQ_API_KEY

logger = logging.getLogger("kairos.rotator")


class KeyRotator:
    """Gerencia pool de API keys com rotação automática."""

    def __init__(self):
        self._google_keys: list[dict] = []
        for i, key in enumerate(GOOGLE_API_KEYS):
            self._google_keys.append({
                "key": key,
                "label": f"google_{i+1}",
                "requests_today": 0,
                "daily_limit": 1500,
                "last_reset": date.today(),
                "last_error": None,
                "cooldown_until": 0,
            })
        self._groq_key = GROQ_API_KEY
        self._current_google_index = 0
        logger.info("KeyRotator inicializado com %d keys Google", len(self._google_keys))

    def _reset_if_new_day(self, entry: dict) -> None:
        """Reseta contadores se é um novo dia."""
        today = date.today()
        if entry["last_reset"] != today:
            entry["requests_today"] = 0
            entry["last_reset"] = today
            entry["cooldown_until"] = 0
            entry["last_error"] = None

    def get_google_key(self) -> str | None:
        """Retorna a próxima key Google disponível (round-robin)."""
        if not self._google_keys:
            logger.error("Nenhuma key Google configurada")
            return None

        now = time.time()
        attempts = 0
        total_keys = len(self._google_keys)

        while attempts < total_keys:
            entry = self._google_keys[self._current_google_index]
            self._reset_if_new_day(entry)

            # Verificar cooldown
            if now < entry["cooldown_until"]:
                logger.debug("Key %s em cooldown", entry["label"])
                self._current_google_index = (self._current_google_index + 1) % total_keys
                attempts += 1
                continue

            # Verificar limite diário
            if entry["requests_today"] >= entry["daily_limit"]:
                logger.warning("Key %s atingiu limite diário (%d)", entry["label"], entry["daily_limit"])
                self._current_google_index = (self._current_google_index + 1) % total_keys
                attempts += 1
                continue

            # Key disponível
            entry["requests_today"] += 1
            key = entry["key"]
            self._current_google_index = (self._current_google_index + 1) % total_keys
            logger.debug("Usando key %s (req #%d)", entry["label"], entry["requests_today"])
            return key

        logger.error("Todas as keys Google esgotadas/em cooldown")
        return None

    def report_error(self, key: str, error_type: str = "rate_limit") -> None:
        """Reporta erro em uma key (coloca em cooldown)."""
        for entry in self._google_keys:
            if entry["key"] == key:
                if error_type == "rate_limit":
                    entry["cooldown_until"] = time.time() + 60  # 1 minuto
                    logger.warning("Key %s em cooldown por rate limit (60s)", entry["label"])
                else:
                    entry["cooldown_until"] = time.time() + 300  # 5 minutos
                    logger.error("Key %s em cooldown por erro '%s' (300s)", entry["label"], error_type)
                entry["last_error"] = error_type
                return

    def get_groq_key(self) -> str | None:
        """Retorna a key Groq (fallback)."""
        if self._groq_key:
            return self._groq_key
        logger.warning("Key Groq não configurada")
        return None

    def get_status(self) -> dict:
        """Retorna status de todas as keys."""
        return {
            "google_keys": [
                {
                    "label": e["label"],
                    "requests_today": e["requests_today"],
                    "daily_limit": e["daily_limit"],
                    "available": e["requests_today"] < e["daily_limit"] and time.time() >= e["cooldown_until"],
                }
                for e in self._google_keys
            ],
            "groq_available": bool(self._groq_key),
        }


# Singleton global
rotator = KeyRotator()
