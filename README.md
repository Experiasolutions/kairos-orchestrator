# KAIROS SKY Orchestrator

Sistema orquestrador autônomo que roda 24/7 na nuvem.

## Estrutura

```
kairos-orchestrator/
├── main.py              → entry point + scheduler
├── config.py            → lê .env do KAIROS (raiz do projeto)
├── supabase_client.py   → conexão + helpers (11 tabelas)
├── model_router.py      → roteamento de modelos por categoria
├── key_rotator.py       → rotação de API keys com cooldown
├── workers/
│   ├── morning_brief.py → gera briefing RPG v2.0
│   ├── night_processor.py → processa check-in + Pareto Score
│   ├── task_worker.py   → executor da task_queue
│   └── context_sync.py  → sync Opus ↔ Orquestrador
├── telegram/
│   └── bot.py           → bot com 10 comandos
├── kairos-supabase-schema.sql → schema completo (11 tabelas)
├── requirements.txt
└── Procfile
```

## Setup Local

```bash
cd kairos-orchestrator
pip install -r requirements.txt
python main.py
```

As variáveis são lidas do `.env` na raiz do projeto KAIROS.

## Deploy Railway

1. Push `kairos-orchestrator/` para um repo GitHub
2. Railway → New Project → Deploy from GitHub
3. Adicionar variáveis de ambiente:
   - SUPABASE_URL
   - SUPABASE_SERVICE_ROLE_KEY
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_ALLOWED_USER_ID
   - GEMINI_API_KEY (ou GOOGLE_API_KEYS para múltiplas)
   - GROQ_API_KEY
4. Deploy automático via push no main

## Bot Telegram — Comandos

| Comando         | Função                                        |
| :-------------- | :-------------------------------------------- |
| /start          | Boas-vindas + lista de comandos               |
| /brief          | Morning Brief completo                        |
| /status         | Status do sistema (level, XP, tasks, dívidas) |
| /quests         | Missões de hoje (com zonas Pareto)            |
| /bosses         | Bosses financeiros (HP bars)                  |
| /task [desc]    | Adicionar task à fila                         |
| /process        | Processar tasks pendentes                     |
| /check          | Iniciar night check-in                        |
| /ask [pergunta] | Perguntar direto à IA                         |
| /sync           | Sincronizar dados do Opus                     |

## Supabase — Schema

Executar `kairos-supabase-schema.sql` no SQL Editor do Supabase.
Non-destructive: só CREATE IF NOT EXISTS.
