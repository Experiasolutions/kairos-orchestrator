# PROMPT PARA O ASSISTENTE DE IA DO SUPABASE
# Cole este prompt no assistente de IA do dashboard Supabase
# Ele irá configurar TUDO automaticamente

---

Preciso configurar um projeto Supabase completo para o meu sistema pessoal chamado KAIROS — um orquestrador de IA pessoal e profissional gamificado como RPG.

## O QUE PRECISO QUE FAÇA:

### 1. Executar o SQL Schema completo abaixo
Execute este SQL no banco de dados. Ele cria 12 tabelas + seed data + triggers + indexes.
Se alguma tabela já existir, só adicione o que falta (respeitar o IF NOT EXISTS).

```sql
-- COPIE E COLE AQUI O CONTEÚDO INTEIRO DO ARQUIVO:
-- kairos-orchestrator/kairos-supabase-schema.sql
```

### 2. Adicionar tabela de Knowledge Brain (cérebro persistente)

```sql
CREATE TABLE IF NOT EXISTS knowledge_brain (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    summary TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    total_chunks INTEGER NOT NULL DEFAULT 1,
    content_chunk TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    last_indexed TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_brain(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_path ON knowledge_brain(file_path);
CREATE INDEX IF NOT EXISTS idx_knowledge_tags ON knowledge_brain USING GIN(tags);
CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_path_chunk ON knowledge_brain(file_path, chunk_index);
```

### 3. Configurar RLS (Row Level Security)

Para TODAS as tabelas exceto `api_keys`:
- Desabilitar RLS (o acesso será via service_role key do backend)
- OU criar policy que permite tudo para authenticated + service_role

Para `api_keys`:
- RLS habilitado
- Apenas service_role pode ler/escrever (NENHUM acesso via anon key)

```sql
-- Desabilitar RLS nas tabelas operacionais (acesso via service_role)
ALTER TABLE profile DISABLE ROW LEVEL SECURITY;
ALTER TABLE quests_daily DISABLE ROW LEVEL SECURITY;
ALTER TABLE bosses_finance DISABLE ROW LEVEL SECURITY;
ALTER TABLE loot_shop DISABLE ROW LEVEL SECURITY;
ALTER TABLE experia_agents DISABLE ROW LEVEL SECURITY;
ALTER TABLE context_store DISABLE ROW LEVEL SECURITY;
ALTER TABLE task_queue DISABLE ROW LEVEL SECURITY;
ALTER TABLE memory_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE leads DISABLE ROW LEVEL SECURITY;
ALTER TABLE clients DISABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_brain DISABLE ROW LEVEL SECURITY;

-- api_keys mantém RLS ativo (proteção extra)
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_only" ON api_keys
    FOR ALL USING (auth.role() = 'service_role');
```

### 4. Criar função de busca por similaridade no Knowledge Brain

```sql
CREATE OR REPLACE FUNCTION search_knowledge(
    search_query TEXT,
    match_category TEXT DEFAULT NULL,
    match_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    file_path TEXT,
    file_name TEXT,
    category TEXT,
    summary TEXT,
    content_chunk TEXT,
    tags TEXT[],
    relevance REAL
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        kb.id,
        kb.file_path,
        kb.file_name,
        kb.category,
        kb.summary,
        kb.content_chunk,
        kb.tags,
        ts_rank(
            to_tsvector('portuguese', kb.summary || ' ' || kb.content_chunk),
            plainto_tsquery('portuguese', search_query)
        ) AS relevance
    FROM knowledge_brain kb
    WHERE
        (match_category IS NULL OR kb.category = match_category)
        AND (
            to_tsvector('portuguese', kb.summary || ' ' || kb.content_chunk)
            @@ plainto_tsquery('portuguese', search_query)
            OR kb.summary ILIKE '%' || search_query || '%'
            OR kb.file_name ILIKE '%' || search_query || '%'
            OR search_query = ANY(kb.tags)
        )
    ORDER BY relevance DESC
    LIMIT match_limit;
END;
$$;
```

### 5. Configurar Realtime

Habilitar Realtime para as tabelas mais importantes para o dashboard:
- `profile`
- `quests_daily`
- `bosses_finance`
- `task_queue`

### 6. Verificar tudo

Após executar, me mostre:
1. Lista de todas as tabelas criadas
2. Contagem de registros em cada tabela
3. Status do RLS em cada tabela
4. Confirmar que os indexes foram criados
5. Confirmar que os triggers de updated_at funcionam

### 7. Me orientar no que não puder fazer automaticamente

Se não puder:
- Habilitar Realtime → me guie no dashboard
- Configurar API keys → me indique onde copiar no Settings > API
- Acessar env vars → me diga o que copiar

## CONTEXTO DO SISTEMA

- **Projeto:** KAIROS — orquestrador de IA pessoal/profissional (RPG gamificado)
- **Backend:** Python no Railway (free tier) conecta via service_role key
- **Frontend:** React (Lovable) conecta via anon key
- **Bot Telegram:** conecta via service_role key
- **Schema:** 12 tabelas (profile, quests, bosses, loot, agents, context_store, task_queue, api_keys, memory_log, leads, clients, knowledge_brain)
- **Dados iniciais:** perfil RPG, 5 dívidas reais como bosses, 17 rewards, 6 leads pipeline

Execute tudo em sequência e me mostre o resultado.
