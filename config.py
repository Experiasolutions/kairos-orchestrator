# Configuração do KAIROS SKY Orchestrator
# Lê variáveis da .env existente do KAIROS (raiz do projeto)
import os
from pathlib import Path

# Carregar .env do projeto raiz se existir
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key and value and key not in os.environ:
                    os.environ[key] = value

# ─── Supabase ──────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

# ─── Telegram (bot KAIROS já existente) ────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_ALLOWED_USER_ID", "")

# ─── Google AI Studio (pool de keys) ──────────────────────
# Suporta GEMINI_API_KEY (single) ou GOOGLE_API_KEYS (comma-separated)
_single_key = os.environ.get("GEMINI_API_KEY", "")
_multi_keys = os.environ.get("GOOGLE_API_KEYS", "")
GOOGLE_API_KEYS = []
if _multi_keys:
    GOOGLE_API_KEYS = [k.strip() for k in _multi_keys.split(",") if k.strip()]
elif _single_key:
    GOOGLE_API_KEYS = [_single_key]

# ─── Groq (fallback) ──────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ─── Ambiente ──────────────────────────────────────────────
ENVIRONMENT = os.environ.get("ENVIRONMENT", os.environ.get("NODE_ENV", "development"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# ─── Horários (BRT = UTC-3) ───────────────────────────────
MORNING_BRIEF_HOUR = 7
MORNING_BRIEF_MINUTE = 0
NIGHT_CHECKIN_HOUR = 22
NIGHT_CHECKIN_MINUTE = 0

# ─── Modelo padrão ────────────────────────────────────────
DEFAULT_MODEL = "gemini-2.0-flash"

# ─── Roteamento de modelos ────────────────────────────────
ROUTING_RULES = {
    "morning_brief": "gemini-2.0-flash",
    "night_processing": "gemini-2.0-flash",
    "lead_analysis": "gemini-2.0-flash",
    "content_draft": "gemini-2.0-flash",
    "code_simple": "gemini-2.0-flash",
    "code_complex": "gemini-2.5-pro",
    "research": "gemini-2.5-pro",
    "data_analysis": "gemini-2.5-pro",
    "sensitive_data": "groq",
}

ROUTING_KEYWORDS = {
    "gemini-2.0-flash": [
        "classifica", "responde", "verifica", "formata",
        "converte", "simples", "rascunho", "lista",
        "resume", "draft", "notifica", "agenda", "confirma",
    ],
    "gemini-2.5-pro": [
        "analisa", "repositório", "código", "arquitetura",
        "refatora", "documento longo",
    ],
    "groq": [
        "cliente", "contrato", "dados pessoais",
        "confidencial", "sensível",
    ],
}
