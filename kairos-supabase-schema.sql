-- ╔═══════════════════════════════════════════════════════════╗
-- ║ KAIROS SUPABASE SCHEMA v1.0                              ║
-- ║ Non-destructive: CREATE IF NOT EXISTS + ALTER TABLE       ║
-- ║ Executar no SQL Editor do Supabase (projeto apex-conductor)║
-- ║ 12 tabelas: profile, quests, bosses, loot, agents,       ║
-- ║ context_store, task_queue, api_keys, memory_log, leads,  ║
-- ║ clients, knowledge_brain                                  ║
-- ╚═══════════════════════════════════════════════════════════╝

-- ═══════════════════════════════════════════════════════════
-- TABLE: profile (atualizar existente)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL DEFAULT 'Gabriel Ferreira',
    class TEXT NOT NULL DEFAULT 'Arquiteto-Comunicador',
    subclass TEXT NOT NULL DEFAULT 'Voice of the Dragonborn',
    level INTEGER NOT NULL DEFAULT 1,
    xp INTEGER NOT NULL DEFAULT 0,
    xp_next_level INTEGER NOT NULL DEFAULT 100,
    gold INTEGER NOT NULL DEFAULT 0,
    streak_count INTEGER NOT NULL DEFAULT 0,
    streak_best INTEGER NOT NULL DEFAULT 0,
    season TEXT NOT NULL DEFAULT 'T1-2026',
    season_day INTEGER NOT NULL DEFAULT 1,
    -- Atributos RPG (escala 0-100)
    attr_energia INTEGER NOT NULL DEFAULT 50,
    attr_foco INTEGER NOT NULL DEFAULT 50,
    attr_forca INTEGER NOT NULL DEFAULT 50,
    attr_prosperidade INTEGER NOT NULL DEFAULT 0,
    attr_clareza INTEGER NOT NULL DEFAULT 50,
    attr_momentum INTEGER NOT NULL DEFAULT 0,
    attr_pareto INTEGER NOT NULL DEFAULT 0,
    -- Pareto tracking
    genius_zone_minutes INTEGER NOT NULL DEFAULT 0,
    genius_zone_target INTEGER NOT NULL DEFAULT 60,
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════
-- TABLE: quests_daily
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS quests_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    block TEXT NOT NULL CHECK (block IN ('aurora', 'raid_i', 'raid_ii', 'santuario', 'vortex', 'semanal')),
    pareto_layer TEXT NOT NULL DEFAULT 'impact' CHECK (pareto_layer IN ('genius', 'excellence', 'impact', 'vortex')),
    is_completed BOOLEAN NOT NULL DEFAULT false,
    xp_reward INTEGER NOT NULL DEFAULT 10,
    gem_reward INTEGER NOT NULL DEFAULT 0,
    seed_reward INTEGER NOT NULL DEFAULT 0,
    quest_date DATE NOT NULL DEFAULT CURRENT_DATE,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════
-- TABLE: bosses_finance (dívidas como bosses RPG)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS bosses_finance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    total_hp NUMERIC(12,2) NOT NULL,
    current_hp NUMERIC(12,2) NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    monthly_cost NUMERIC(12,2) DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'negotiating', 'agreement', 'defeated')),
    strategy TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════
-- TABLE: loot_shop (rewards por tier)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS loot_shop (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('pessoal', 'castelo', 'trabalho')),
    tier INTEGER NOT NULL CHECK (tier BETWEEN 1 AND 6),
    cost_gold INTEGER NOT NULL DEFAULT 0,
    required_level INTEGER NOT NULL DEFAULT 1,
    is_unlocked BOOLEAN NOT NULL DEFAULT false,
    is_redeemed BOOLEAN NOT NULL DEFAULT false,
    unlock_requirement TEXT,
    estimated_cost_brl NUMERIC(12,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════
-- TABLE: experia_agents
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS experia_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('active', 'idle', 'error', 'deployed')),
    performance_metric NUMERIC(5,2) DEFAULT 0,
    last_active TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════
-- TABLE: context_store (memória compartilhada Opus ↔ Orquestrador)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS context_store (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT NOT NULL UNIQUE,
    value JSONB NOT NULL,
    updated_by TEXT NOT NULL DEFAULT 'system' CHECK (updated_by IN ('opus', 'orchestrator', 'system', 'gabriel')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════
-- TABLE: task_queue (fila de execução automática)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS task_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL DEFAULT 'general',
    priority INTEGER NOT NULL DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    model_override TEXT,
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    created_by TEXT NOT NULL DEFAULT 'system',
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════
-- TABLE: api_keys (pool rotacionado — RLS protegido)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL CHECK (provider IN ('google', 'groq', 'openai', 'anthropic')),
    key_value TEXT NOT NULL,
    label TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    requests_today INTEGER NOT NULL DEFAULT 0,
    daily_limit INTEGER NOT NULL DEFAULT 1500,
    last_used TIMESTAMPTZ,
    last_reset DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════
-- TABLE: memory_log (journaling + decisões)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS memory_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    log_type TEXT NOT NULL CHECK (log_type IN ('journal', 'decision', 'insight', 'morning_brief', 'night_checkin', 'system')),
    content TEXT NOT NULL,
    metadata JSONB,
    mood_score INTEGER CHECK (mood_score BETWEEN 1 AND 5),
    energy_score INTEGER CHECK (energy_score BETWEEN 1 AND 5),
    pareto_score JSONB,
    log_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════
-- TABLE: leads (pipeline Experia)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name TEXT NOT NULL,
    contact_name TEXT,
    phone TEXT,
    email TEXT,
    market TEXT NOT NULL DEFAULT 'local' CHECK (market IN ('local', 'regional', 'industrial', 'outreach')),
    approach TEXT,
    status TEXT NOT NULL DEFAULT 'prospect' CHECK (status IN ('prospect', 'contacted', 'meeting', 'proposal', 'negotiation', 'closed_won', 'closed_lost')),
    notes TEXT,
    next_action TEXT,
    next_action_date DATE,
    estimated_mrr NUMERIC(12,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════
-- TABLE: clients (clientes ativos)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name TEXT NOT NULL,
    contact_name TEXT,
    phone TEXT,
    email TEXT,
    market TEXT NOT NULL,
    mrr NUMERIC(12,2) NOT NULL DEFAULT 0,
    contract_type TEXT CHECK (contract_type IN ('permuta', 'mensal', 'projeto', 'enterprise')),
    start_date DATE,
    services JSONB,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'churned')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════
-- SEED DATA
-- ═══════════════════════════════════════════════════════════

-- Profile inicial
INSERT INTO profile (name, class, subclass, level, xp, season, season_day)
VALUES ('Gabriel Ferreira', 'Arquiteto-Comunicador', 'Voice of the Dragonborn', 1, 0, 'T1-2026', 1)
ON CONFLICT DO NOTHING;

-- Bosses financeiros REAIS
INSERT INTO bosses_finance (name, description, total_hp, current_hp, priority, monthly_cost, strategy) VALUES
('Serasa Total', 'Dívidas Serasa (R$3.155 + empréstimos)', 9591.00, 9591.00, 'critical', 0, 'Contatar para acordo com desconto'),
('Soma Mensal', 'Parcelas recorrentes R$269/mês', 2293.00, 2293.00, 'high', 269.00, 'Fazer acordo com entrada mínima'),
('Enel', 'Energia acumulada R$1.079', 1079.00, 1079.00, 'high', 0, 'Negociar parcelamento'),
('IPTU', 'Imposto predial acumulado', 10000.00, 10000.00, 'low', 0, 'Planejar após estabilizar receita'),
('CDHU', 'Financiamento habitacional', 5880.00, 5880.00, 'low', 0, 'Planejar após estabilizar receita')
ON CONFLICT DO NOTHING;

-- Loot Shop com rewards REAIS
INSERT INTO loot_shop (item_name, category, tier, estimated_cost_brl, unlock_requirement) VALUES
('Skincare/Haircare Products', 'pessoal', 1, 100.00, '1 semana missões completas'),
('Underwear Nova', 'pessoal', 1, 80.00, '1 semana missões completas'),
('Roupas Novas', 'pessoal', 2, 300.00, '2 semanas consecutivas'),
('Botas Novas', 'pessoal', 2, 400.00, '2 semanas consecutivas'),
('Extração Dentária', 'pessoal', 3, 800.00, '1 mês + 1 marco'),
('MMA Gym', 'pessoal', 4, 1500.00, '1 regional fechado'),
('Natação', 'pessoal', 4, 1200.00, '1 regional fechado'),
('Tatuagens', 'pessoal', 5, 3000.00, '3 meses consecutivos'),
('Projetor + Videogame', 'pessoal', 6, 5000.00, 'Boss T1 derrotado'),
('Limpar e Organizar Apê', 'castelo', 1, 0.00, 'Custo zero — só disposição'),
('Reformar Azulejo Cozinha', 'castelo', 2, 500.00, '2 semanas consecutivas'),
('Trocar Armários e Bancada', 'castelo', 3, 2000.00, '1 mês + marco'),
('Cadeira de Trabalho Nova', 'trabalho', 1, 600.00, '1 semana completa'),
('Notebook para Trabalho', 'trabalho', 2, 2500.00, '2 semanas consecutivas'),
('Celular Melhor Qualidade', 'trabalho', 3, 1500.00, '1 mês + marco'),
('Fone/Microfone Portáteis', 'trabalho', 4, 800.00, '1 regional fechado'),
('Headset Profissional', 'trabalho', 5, 1200.00, '3 meses consecutivos')
ON CONFLICT DO NOTHING;

-- Context Store inicial
INSERT INTO context_store (key, value, updated_by) VALUES
('system_state', '{"status": "initializing", "version": "3.0", "season": "T1-2026"}', 'system'),
('last_session', '{"decisions": [], "directives": [], "next_tasks": []}', 'system'),
('operator_profile', '{"archetype": "Dragonborn", "genius_zone": ["comunicação vocal", "arquitetura de sistemas", "narrativa transformadora"], "weakness": "execução disciplinada"}', 'system'),
('pareto_config', '{"genius_target_minutes": 60, "vortex_day": "friday", "vortex_hours": "14-16"}', 'system')
ON CONFLICT (key) DO NOTHING;

-- Experia agents
INSERT INTO experia_agents (agent_name, role, status) VALUES
('KAIROS Core', 'Orquestrador', 'active'),
('Prospecção', 'BDR', 'idle'),
('Vendas', 'Closer', 'idle'),
('Entrega', 'Worker', 'idle'),
('Analista', 'Research', 'idle')
ON CONFLICT DO NOTHING;

-- Leads pipeline inicial (do RP Estratégia)
INSERT INTO leads (business_name, market, approach, status, notes) VALUES
('Miranda (Assistência Técnica)', 'local', 'visita presencial', 'prospect', 'Operação Mauá'),
('Leandro (Bazar)', 'local', 'pitch permuta', 'prospect', 'Operação Mauá'),
('Rouxinol (PetShop)', 'local', 'pitch permuta (ração Tigrinho)', 'prospect', 'Operação Mauá'),
('Marmitaria Local', 'local', 'pitch permuta (alimentação)', 'prospect', 'Operação Mauá'),
('Master Pumps', 'industrial', 'trojan horse via RH', 'prospect', 'Operação Master Pumps — via cunhado'),
('Elaine', 'local', 'MVP direto', 'proposal', 'Entrega amanhã')
ON CONFLICT DO NOTHING;

-- ═══════════════════════════════════════════════════════════
-- RLS (Row Level Security) — proteger api_keys
-- ═══════════════════════════════════════════════════════════
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Indexes para performance
CREATE INDEX IF NOT EXISTS idx_quests_date ON quests_daily(quest_date);
CREATE INDEX IF NOT EXISTS idx_task_queue_status ON task_queue(status, priority);
CREATE INDEX IF NOT EXISTS idx_memory_log_date ON memory_log(log_date);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_context_store_key ON context_store(key);

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers de updated_at
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at_profile') THEN
        CREATE TRIGGER set_updated_at_profile BEFORE UPDATE ON profile FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at_bosses') THEN
        CREATE TRIGGER set_updated_at_bosses BEFORE UPDATE ON bosses_finance FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at_context') THEN
        CREATE TRIGGER set_updated_at_context BEFORE UPDATE ON context_store FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at_leads') THEN
        CREATE TRIGGER set_updated_at_leads BEFORE UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at_clients') THEN
        CREATE TRIGGER set_updated_at_clients BEFORE UPDATE ON clients FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- ═══════════════════════════════════════════════════════════
-- TABLE: knowledge_brain (memória persistente — "cérebro de elefante")
-- ═══════════════════════════════════════════════════════════
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

-- Função de busca no Knowledge Brain (full-text search em português)
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

-- ═══════════════════════════════════════════════════════════
-- RLS — desabilitar nas tabelas operacionais (acesso via service_role)
-- ═══════════════════════════════════════════════════════════
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
