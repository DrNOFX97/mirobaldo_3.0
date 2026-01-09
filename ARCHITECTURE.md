# 🏗️ Arquitetura do Mirobaldo 3.0

## Visão Geral

O Mirobaldo 3.0 combina o melhor de dois projetos:
1. **chatbot_2.0**: Sistema RAG avançado com IA
2. **mirobaldo**: Sistema de dados em tempo real

---

## 📐 Arquitetura de Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Interface   │  │  Adaptive    │  │  Mirobaldo   │      │
│  │  Moderna     │  │  Frontend    │  │  Classic     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     API GATEWAY                              │
│              (Roteamento de Requisições)                     │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
┌──────────────────────┐    ┌──────────────────────┐
│   BACKEND RAG        │    │   BACKEND FLASK      │
│   (chatbot_2.0)      │    │   (mirobaldo)        │
│                      │    │                      │
│  ┌────────────────┐ │    │  ┌────────────────┐ │
│  │ Adaptive RAG   │ │    │  │ Last Matches   │ │
│  │ Hybrid RAG     │ │    │  │ Next Matches   │ │
│  │ RAG Reranker   │ │    │  │ Classification │ │
│  └────────────────┘ │    │  │ Game Reports   │ │
│                      │    │  └────────────────┘ │
│  ┌────────────────┐ │    │                      │
│  │ Agent Router   │ │    │  ┌────────────────┐ │
│  │ - Biography    │ │    │  │ SQLite DB      │ │
│  │ - Results      │ │    │  │ Live Scraping  │ │
│  │ - Class.       │ │    │  └────────────────┘ │
│  └────────────────┘ │    │                      │
└──────────────────────┘    └──────────────────────┘
           │                           │
           └───────────┬───────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ Historical │  │  SQLite    │  │  External  │            │
│  │ JSON Data  │  │  Database  │  │  Sources   │            │
│  │ (54 épocas)│  │  (Jogos)   │  │  (Scraper) │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ 206 Bios   │  │ Fotografias│  │ Plantéis   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   AI SERVICES                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  OpenAI    │  │  Vector    │  │  Embeddings│            │
│  │  GPT-4     │  │  Search    │  │  System    │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Fluxo de Dados

### 1. Query do Utilizador
```
Utilizador → Frontend → API Gateway
```

### 2. Roteamento Inteligente
```
API Gateway analisa query:
├─ Dados históricos/biográficos → Backend RAG
└─ Dados atuais/ao vivo → Backend Flask
```

### 3. Processamento RAG (Histórico)
```
Query → Agent Router → Agente Especializado
                          │
                          ├─ Biography Agent (biografias)
                          ├─ Results Agent (resultados)
                          └─ Classification Agent (classificações)
                          │
                          ▼
               Retrieval System (RAG)
                          │
                          ├─ Adaptive RAG
                          ├─ Hybrid RAG
                          └─ Reranker
                          │
                          ▼
                  Historical Data
                          │
                          ▼
                    OpenAI GPT-4
                          │
                          ▼
                   Resposta Contextual
```

### 4. Processamento Flask (Tempo Real)
```
Query → Flask Router
           │
           ├─ last_matches.py → Web Scraping → Resultados
           ├─ next_matches.py → Web Scraping → Próximos Jogos
           ├─ classificação.py → Web Scraping → Tabela
           └─ game_report.py → SQLite DB → Relatório
           │
           ▼
      Resposta Estruturada
```

### 5. Resposta Final
```
Backend → API Gateway → Frontend → Utilizador
```

---

## 🧩 Componentes Principais

### Backend RAG (Python)
**Localização**: `backend/`

#### Sistemas RAG
- `adaptive_rag_system.py`: RAG que se adapta ao tipo de query
- `hybrid_rag_reranker.py`: Combina múltiplas estratégias de retrieval
- `hybrid_rag_system.py`: Sistema híbrido de recuperação
- `rag_system.py`: Sistema base de RAG
- `llm_interface.py`: Interface com LLMs (OpenAI)

#### Agentes Especializados
- `agent_router.py`: Roteia queries para agentes apropriados
- `biography_agent.py`: Especialista em biografias
- `classification_agent.py`: Especialista em classificações
- `results_agent.py`: Especialista em resultados

### Backend Flask (Python)
**Localização**: `backend/`

#### Módulos de Dados
- `app.py`: Aplicação Flask principal
- `last_matches.py`: Extrai últimos jogos
- `next_matches.py`: Extrai próximos jogos
- `classificação.py`: Extrai tabela classificativa
- `game_report.py`: Gera relatórios de jogos
- `utils.py`: Utilitários comuns

### Frontend
**Localização**: `frontend/`

#### Interfaces
- `public/`: Frontend moderno (chatbot_2.0)
- `mirobaldo_src/`: Frontend clássico (mirobaldo)
- `frontend_adaptive.html`: Interface adaptativa

### Data Layer
**Localização**: `data/`

#### Dados Históricos
- `chatbot_dados/`: Dados completos do chatbot_2.0
  - `biografias/`: 206 biografias
  - `classificacoes/`: Classificações históricas
  - `resultados/`: Resultados históricos
  - `jogadores/`: Dados de jogadores
  - `fotografias/`: Imagens
  - `historia/`: História do clube

#### Dados Estruturados
- `Planteis/`: 54 épocas de plantéis
- `Detalhes jogadores/`: 54 épocas de detalhes
- `dados_jogos.db`: Base de dados SQLite
- `50_anos.json`: 50 anos de história
- `hist_result.json`: Histórico completo
- `antonio_gago.json`: Dados específicos

---

## 🔐 Segurança

### API Keys
- Armazenadas em `.env` (não versionado)
- Nunca expostas no frontend
- Rotação periódica recomendada

### Dados
- Sanitização de inputs
- Validação de queries
- Rate limiting (futuro)

---

## ⚡ Performance

### Caching
- RAG cache para queries frequentes
- Cache de scraping (TTL configurável)
- Cache de embeddings

### Otimizações
- Lazy loading de dados
- Compressão de respostas
- Indexação de dados históricos

---

## 🧪 Testes

### Testes Unitários
- Backend RAG: `backend/test_rag.py`
- Agentes: `tests/test_agents.py`
- Módulos Flask: `tests/test_flask.py`

### Testes de Integração
- End-to-end: `tests/test_e2e.py`
- API: `tests/test_api.py`

---

## 📈 Escalabilidade

### Horizontal
- Backend stateless (fácil de replicar)
- Load balancing entre instâncias
- Cache distribuído (Redis futuro)

### Vertical
- Otimização de queries
- Índices em bases de dados
- Compressão de dados

---

## 🔮 Futuro

### Melhorias Planeadas
1. **API Gateway unificado** (Express.js ou FastAPI)
2. **Cache distribuído** (Redis)
3. **Queue system** para scraping (Celery)
4. **Monitorização** (Prometheus + Grafana)
5. **CI/CD Pipeline**
6. **Containerização** (Docker)
7. **Orquestração** (Kubernetes)

### Novas Funcionalidades
1. **WebSockets** para updates em tempo real
2. **GraphQL API** para queries flexíveis
3. **Machine Learning** para previsões
4. **Análise de sentimento** de notícias
5. **Notificações push**

---

## 🛠️ Manutenção

### Logs
- Centralizados em `logs/`
- Rotação automática
- Níveis: DEBUG, INFO, WARNING, ERROR

### Monitoring
- Health checks: `/health`
- Métricas: `/metrics`
- Status: `/status`

### Backup
- Dados históricos: Imutáveis
- SQLite DB: Backup diário
- Configurações: Versionadas

---

## 📚 Recursos Adicionais

- [README.md](README.md) - Visão geral do projeto
- [QUICK_START.md](docs/QUICK_START.md) - Guia rápido
- [API_DOCS.md](docs/API_DOCS.md) - Documentação da API
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) - Guia de contribuição

---

<div align="center">

**Arquitetura projetada com ❤️ para o SC Farense**

🦁 **SEMPRE FARENSE!** 🦁

</div>
