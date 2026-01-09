<div align="center">

# 🦁 Mirobaldo 3.0

### Chatbot Inteligente do Sporting Clube Farense

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

**A fusão definitiva do melhor de dois mundos: IA avançada + Dados em tempo real**

[Funcionalidades](#-funcionalidades) •
[Instalação](#-instalação) •
[Como Usar](#-como-usar) •
[Documentação](#-documentação) •
[Contribuir](#-contribuir)

<img src="https://img.shields.io/badge/Status-Em_Desenvolvimento-orange?style=for-the-badge" />

</div>

---

## 📖 Sobre o Projeto

**Mirobaldo 3.0** é um assistente virtual inteligente dedicado à história e memória do **Sporting Clube Farense**. Combinando tecnologia de ponta com dados históricos extensivos, o Mirobaldo oferece uma experiência única para adeptos e interessados no clube algarvio.

### 🎯 O Que Torna o Mirobaldo 3.0 Especial?

- 🧠 **Sistema RAG Avançado** com múltiplas estratégias (Adaptive, Hybrid, Reranker)
- 🤖 **Agentes Especializados** para biografias, resultados e classificações
- 📊 **206 Biografias** detalhadas de jogadores, treinadores e figuras históricas
- ⚽ **54 Épocas** completas de dados históricos (1970-2024)
- 🔴 **Dados em Tempo Real** via web scraping
- 💬 **Interface Conversacional** natural e intuitiva

---

## ✨ Funcionalidades

### 🤖 Inteligência Artificial

<table>
<tr>
<td width="50%">

#### Sistema RAG Multi-Estratégia
- **Adaptive RAG**: Adapta-se ao tipo de pergunta
- **Hybrid RAG**: Combina múltiplas estratégias
- **Reranker**: Otimiza relevância das respostas
- **Vector Search**: ChromaDB para busca semântica
- **Embeddings**: Sentence Transformers

</td>
<td width="50%">

#### Agentes Especializados
- 👤 **Biography Agent**: Especialista em biografias
- 📈 **Results Agent**: Análise de resultados
- 🏆 **Classification Agent**: Classificações e tabelas
- 🎯 **Router**: Direcionamento inteligente de queries

</td>
</tr>
</table>

### 📊 Base de Dados

<table>
<tr>
<td width="33%">

#### Dados Históricos
- 📁 206 biografias completas
- 📅 54 épocas (1970-2024)
- ⚽ Resultados jogo a jogo
- 📊 Classificações completas
- 📷 Fotografias históricas
- 📚 História do clube

</td>
<td width="33%">

#### Dados em Tempo Real
- 🔴 Últimos jogos (live)
- 📅 Próximos jogos agendados
- 📊 Classificação atual
- 📈 Relatórios de jogo
- 🎯 Estatísticas atualizadas

</td>
<td width="33%">

#### Estrutura de Dados
- 🗄️ Base SQLite (dados jogos)
- 📄 JSON estruturado (histórico)
- 🖼️ Fotografias organizadas
- 📊 Plantéis por época
- 👥 Detalhes de jogadores

</td>
</tr>
</table>

### 🎨 Interface

- 💻 **Web Interface**: Interface moderna e responsiva
- 🎯 **Chat Adaptativo**: Conversação natural
- 📱 **Design Responsivo**: Desktop e mobile
- 🎨 **Múltiplos Temas**: Clássico e moderno

---

## 🚀 Instalação

### Pré-requisitos

```bash
Python 3.8+
pip (gerenciador de pacotes Python)
```

### Instalação Rápida

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/mirobaldo_3.0.git
cd mirobaldo_3.0

# 2. Execute o script de instalação
chmod +x start.sh
./start.sh
```

### Instalação Manual

<details>
<summary>Clique para ver instruções detalhadas</summary>

```bash
# 1. Criar ambiente virtual
python3 -m venv venv

# 2. Ativar ambiente virtual
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 3. Instalar dependências
pip install -r requirements_chatbot.txt
pip install -r requirements_mirobaldo.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
nano .env  # Adicionar OPENAI_API_KEY

# 5. Iniciar aplicação
cd backend
python app.py
```

</details>

### Configuração

Edite o arquivo `.env` e adicione suas credenciais:

```env
OPENAI_API_KEY=sua_chave_aqui
FLASK_PORT=5001
DATABASE_PATH=data/dados_jogos.db
RAG_MODEL=gpt-4o-mini
```

---

## 💻 Como Usar

### Iniciar o Servidor

```bash
# Método 1: Script automático (recomendado)
./start.sh

# Método 2: Manual
source venv/bin/activate
cd backend
python app.py
```

### Acessar a Aplicação

Abra seu navegador em: **http://localhost:5001**

### Exemplos de Perguntas

<table>
<tr>
<td width="50%">

#### 📚 Consultas Biográficas
```
"Quem foi António Gago?"
"Conta-me sobre a carreira de [jogador]"
"Quais foram os melhores marcadores?"
```

#### 🏆 Dados Históricos
```
"Como foi a época 1994/1995?"
"Quantos títulos o Farense tem?"
"Qual foi a maior série invicta?"
```

</td>
<td width="50%">

#### ⚽ Dados Atuais
```
"Quais foram os últimos jogos?"
"Qual é a classificação atual?"
"Quando é o próximo jogo?"
```

#### 📊 Estatísticas
```
"Quantos jogos em casa ganhámos?"
"Qual o melhor marcador da história?"
"Estatísticas da época atual"
```

</td>
</tr>
</table>

### API Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Página principal |
| `/chat` | GET/POST | Interface de chat |
| `/api/last_matches` | GET | Últimos jogos |
| `/api/next_matches` | GET | Próximos jogos |
| `/api/classification` | GET | Classificação atual |
| `/api/biography/<player>` | GET | Biografia de jogador |

---

## 📁 Estrutura do Projeto

```
mirobaldo_3.0/
├── 📂 backend/                 # Backend Python
│   ├── 🐍 app.py              # Aplicação Flask principal
│   ├── 🤖 chatbot.py          # Lógica do chatbot
│   ├── 🧠 adaptive_rag_system.py
│   ├── 🔀 hybrid_rag_system.py
│   ├── 🎯 hybrid_rag_reranker.py
│   ├── 📊 last_matches.py     # Últimos jogos
│   ├── 📅 next_matches.py     # Próximos jogos
│   ├── 🏆 classificação.py    # Classificação
│   └── 📈 game_report.py      # Relatórios
│
├── 🤖 agents/                  # Agentes especializados
│   ├── agent_router.py
│   ├── biography_agent.py
│   ├── classification_agent.py
│   └── results_agent.py
│
├── 💾 data/                    # Dados
│   ├── 📊 chatbot_dados/      # Dados chatbot_2.0
│   │   ├── biografias/        # 206 biografias
│   │   ├── classificacoes/
│   │   ├── resultados/
│   │   ├── jogadores/
│   │   └── fotografias/
│   ├── 👥 Planteis/           # 54 épocas
│   ├── ⚽ Detalhes jogadores/ # 54 épocas
│   └── 🗄️ dados_jogos.db     # Base SQLite
│
├── 🎨 frontend/               # Interface
│   ├── public/                # Frontend moderno
│   ├── mirobaldo_src/         # Frontend clássico
│   └── frontend_adaptive.html
│
├── 📚 docs/                   # Documentação
│   └── ARCHITECTURE.md        # Arquitetura detalhada
│
├── 📝 README.md               # Este arquivo
├── ⚙️ .env                    # Variáveis de ambiente
├── 🚀 start.sh                # Script de lançamento
└── 📦 requirements*.txt       # Dependências
```

---

## 🔧 Tecnologias

### Backend
- **Python 3.13** - Linguagem principal
- **Flask 3.1.2** - Framework web
- **OpenAI GPT-4** - Inteligência artificial
- **ChromaDB** - Vector database
- **Sentence Transformers** - Embeddings
- **BeautifulSoup4** - Web scraping
- **Pandas** - Análise de dados
- **SQLite** - Base de dados

### Frontend
- **HTML5/CSS3** - Interface
- **JavaScript** - Interatividade
- **Fetch API** - Comunicação

### AI/ML
- **PyTorch** - Deep learning
- **Sentence-Transformers** - Embeddings semânticos
- **Tiktoken** - Tokenização
- **scikit-learn** - Machine learning

---

## 📊 Estatísticas do Projeto

<div align="center">

| Métrica | Valor |
|---------|-------|
| 💾 Tamanho | 1.7 GB |
| 📄 Ficheiros | 3,588 |
| 👤 Biografias | 206 |
| 📅 Épocas Cobertas | 54 (1970-2024) |
| ⚽ Jogadores | Milhares |
| 🏆 Jogos Registados | Milhares |
| 📷 Fotografias | Centenas |
| 🤖 Agentes IA | 3 especializados |

</div>

---

## 📖 Documentação

### Guias Disponíveis

- 📘 [**README.md**](README.md) - Guia principal (você está aqui)
- 🏗️ [**ARCHITECTURE.md**](ARCHITECTURE.md) - Arquitetura detalhada do sistema
- 🚀 [**QUICK_START.md**](docs/QUICK_START.md) - Início rápido
- 📡 [**API_DOCS.md**](docs/API_DOCS.md) - Documentação da API
- 🤝 [**CONTRIBUTING.md**](docs/CONTRIBUTING.md) - Como contribuir

### Arquitetura

O Mirobaldo 3.0 utiliza uma arquitetura híbrida:

```
Frontend → API Gateway → [ Backend RAG | Backend Flask ] → Data Layer → AI Services
```

Para detalhes completos, consulte [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 🗺️ Roadmap

### ✅ Versão 3.0 (Atual)
- [x] Fusão de projetos chatbot_2.0 + mirobaldo
- [x] Sistema RAG avançado integrado
- [x] Agentes especializados
- [x] Dados históricos completos (54 épocas)
- [x] Interface web funcional
- [ ] Backend híbrido totalmente integrado
- [ ] Testes automatizados completos

### 🔮 Versão 3.1 (Próxima)
- [ ] API REST unificada e documentada
- [ ] Dashboard de administração
- [ ] Sistema de cache otimizado (Redis)
- [ ] Suporte multilíngue (PT/EN/ES)
- [ ] Autenticação de usuários
- [ ] Histórico de conversas

### 🚀 Versão 3.2+ (Futuro)
- [ ] App móvel (iOS/Android)
- [ ] Machine Learning para previsões de jogos
- [ ] Análise de sentimento de notícias
- [ ] Integração com redes sociais
- [ ] Notificações em tempo real
- [ ] Sistema de recomendações
- [ ] Voice chat (voz)
- [ ] Gamificação para adeptos

---

## 🤝 Contribuir

Contribuições são bem-vindas! Aqui está como você pode ajudar:

### Como Contribuir

1. **Fork** o projeto
2. Crie uma **branch** para sua feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** suas mudanças (`git commit -m 'Add: Amazing Feature'`)
4. **Push** para a branch (`git push origin feature/AmazingFeature`)
5. Abra um **Pull Request**

### Diretrizes

- Siga o estilo de código existente
- Adicione testes para novas funcionalidades
- Atualize a documentação
- Descreva claramente suas mudanças

### Áreas de Contribuição

- 🐛 **Bug Fixes** - Correção de bugs
- ✨ **Features** - Novas funcionalidades
- 📝 **Documentação** - Melhorias na documentação
- 🎨 **Design** - Interface e UX
- 🧪 **Testes** - Testes automatizados
- 🌐 **Tradução** - Internacionalização

---

## 🐛 Reportar Bugs

Encontrou um bug? [Abra uma issue](https://github.com/seu-usuario/mirobaldo_3.0/issues/new?template=bug_report.md)

Inclua:
- Descrição clara do problema
- Passos para reproduzir
- Comportamento esperado vs. atual
- Screenshots (se aplicável)
- Ambiente (OS, Python version, etc.)

---

## 💡 Sugerir Features

Tem uma ideia? [Abra uma issue](https://github.com/seu-usuario/mirobaldo_3.0/issues/new?template=feature_request.md)

Descreva:
- O problema que a feature resolve
- Solução proposta
- Alternativas consideradas
- Contexto adicional

---

## 📄 Licença

Este projeto está licenciado sob a **MIT License** - veja o arquivo [LICENSE](LICENSE) para detalhes.

```
MIT License

Copyright (c) 2025 F. Nuno

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

[...]
```

---

## 👨‍💻 Autor

<div align="center">

**F. Nuno**

Desenvolvedor apaixonado pelo Sporting Clube Farense 🦁

[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/seu-usuario)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/seu-perfil)
[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:seu-email@example.com)

</div>

---

## 🙏 Agradecimentos

- 🦁 **Sporting Clube Farense** - Pela inspiração
- 🤖 **OpenAI** - Pela tecnologia GPT-4
- 🌐 **Comunidade Open Source** - Pelas ferramentas incríveis
- ⚽ **Adeptos do Farense** - Pelo apoio e feedback

---

## 📞 Suporte

Precisa de ajuda? Temos várias opções:

- 📖 [**Documentação**](docs/)
- 💬 [**Discussions**](https://github.com/seu-usuario/mirobaldo_3.0/discussions)
- 🐛 [**Issues**](https://github.com/seu-usuario/mirobaldo_3.0/issues)
- 📧 [**Email**](mailto:seu-email@example.com)

---

## ⭐ Star History

Se este projeto foi útil para você, considere dar uma ⭐!

[![Star History Chart](https://api.star-history.com/svg?repos=seu-usuario/mirobaldo_3.0&type=Date)](https://star-history.com/#seu-usuario/mirobaldo_3.0&Date)

---

<div align="center">

### 🔴⚫ Feito com ❤️ para o Sporting Clube Farense 🔴⚫

**SEMPRE FARENSE!** 🦁⚽

---

[![forthebadge](https://forthebadge.com/images/badges/made-with-python.svg)](https://forthebadge.com)
[![forthebadge](https://forthebadge.com/images/badges/built-with-love.svg)](https://forthebadge.com)
[![forthebadge](https://forthebadge.com/images/badges/powered-by-coffee.svg)](https://forthebadge.com)

---

**[⬆ Voltar ao topo](#-mirobaldo-30)**

</div>
