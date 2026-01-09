# 🤝 Guia de Contribuição - Mirobaldo 3.0

Obrigado pelo seu interesse em contribuir para o **Mirobaldo 3.0**! Este documento fornece diretrizes para tornar o processo de contribuição simples e eficaz.

---

## 📋 Índice

- [Código de Conduta](#código-de-conduta)
- [Como Posso Contribuir?](#como-posso-contribuir)
- [Configuração do Ambiente](#configuração-do-ambiente)
- [Processo de Desenvolvimento](#processo-de-desenvolvimento)
- [Padrões de Código](#padrões-de-código)
- [Commits e Pull Requests](#commits-e-pull-requests)
- [Reportar Bugs](#reportar-bugs)
- [Sugerir Features](#sugerir-features)

---

## 📜 Código de Conduta

Ao participar deste projeto, você concorda em manter um ambiente respeitoso e inclusivo para todos. Esperamos:

- ✅ Respeito mútuo entre contribuidores
- ✅ Feedback construtivo e profissional
- ✅ Foco em melhorias técnicas
- ❌ Linguagem ofensiva ou discriminatória
- ❌ Ataques pessoais ou trolling

---

## 🎯 Como Posso Contribuir?

### 1. 🐛 Reportar Bugs

Encontrou um bug? Siga estes passos:

1. Verifique se o bug já foi reportado nas [Issues](https://github.com/seu-usuario/mirobaldo_3.0/issues)
2. Se não encontrar, [crie uma nova issue](https://github.com/seu-usuario/mirobaldo_3.0/issues/new?template=bug_report.md)
3. Use o template de bug report
4. Inclua o máximo de detalhes possível

### 2. ✨ Propor Features

Tem uma ideia para melhorar o Mirobaldo?

1. Verifique se a feature já foi sugerida
2. [Abra uma issue](https://github.com/seu-usuario/mirobaldo_3.0/issues/new?template=feature_request.md)
3. Descreva claramente o problema e a solução proposta
4. Aguarde feedback da comunidade

### 3. 💻 Contribuir com Código

Quer implementar uma feature ou corrigir um bug?

1. Faça fork do projeto
2. Crie uma branch para sua feature
3. Implemente as mudanças
4. Escreva testes
5. Envie um Pull Request

### 4. 📝 Melhorar Documentação

A documentação nunca está perfeita! Você pode:

- Corrigir erros de ortografia/gramática
- Adicionar exemplos práticos
- Traduzir documentação
- Melhorar explicações técnicas

### 5. 🎨 Design e UX

Contribuições de design são bem-vindas:

- Melhorias na interface
- Novos temas visuais
- Ícones e ilustrações
- Experiência do usuário

---

## 🛠️ Configuração do Ambiente

### Pré-requisitos

- Python 3.8+
- Git
- Editor de código (VSCode recomendado)

### Setup Inicial

```bash
# 1. Fork e clone o repositório
git clone https://github.com/SEU-USUARIO/mirobaldo_3.0.git
cd mirobaldo_3.0

# 2. Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 3. Instalar dependências de desenvolvimento
pip install -r requirements_chatbot.txt
pip install -r requirements_mirobaldo.txt
pip install -r requirements_dev.txt  # Se existir

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações

# 5. Rodar testes para verificar setup
pytest tests/
```

---

## 🔄 Processo de Desenvolvimento

### 1. Criar Branch

```bash
# Para features
git checkout -b feature/nome-da-feature

# Para bugs
git checkout -b fix/nome-do-bug

# Para documentação
git checkout -b docs/descricao

# Para melhorias
git checkout -b improvement/descricao
```

### 2. Fazer Mudanças

- Mantenha commits pequenos e focados
- Teste suas mudanças localmente
- Siga os padrões de código

### 3. Executar Testes

```bash
# Rodar todos os testes
pytest

# Rodar testes específicos
pytest tests/test_agents.py

# Rodar com coverage
pytest --cov=backend tests/
```

### 4. Commit

```bash
git add .
git commit -m "tipo: descrição curta

Descrição detalhada do que foi alterado e por quê.

Closes #123"  # Se aplicável
```

### 5. Push e Pull Request

```bash
git push origin feature/nome-da-feature
```

Então abra um Pull Request no GitHub.

---

## 📐 Padrões de Código

### Python

Seguimos [PEP 8](https://pep8.org/) com algumas adaptações:

```python
# ✅ BOM
def calcular_estatisticas(jogos: list) -> dict:
    """
    Calcula estatísticas de uma lista de jogos.

    Args:
        jogos: Lista de objetos Jogo

    Returns:
        Dicionário com estatísticas calculadas
    """
    total = len(jogos)
    vitorias = sum(1 for j in jogos if j.resultado == "vitória")
    return {"total": total, "vitorias": vitorias}

# ❌ MAU
def calc(j):
    t=len(j)
    v=sum(1 for x in j if x.resultado=="vitória")
    return {"total":t,"vitorias":v}
```

### Formatação

Use **Black** para formatação automática:

```bash
pip install black
black backend/
```

### Linting

Use **Flake8** para verificar código:

```bash
pip install flake8
flake8 backend/
```

### Type Hints

Use type hints sempre que possível:

```python
from typing import List, Dict, Optional

def processar_biografias(
    biografias: List[Dict[str, str]],
    filtro: Optional[str] = None
) -> List[Dict[str, str]]:
    """Processa lista de biografias."""
    if filtro:
        return [b for b in biografias if filtro in b.get("nome", "")]
    return biografias
```

---

## 📝 Commits e Pull Requests

### Mensagens de Commit

Siga o [Conventional Commits](https://www.conventionalcommits.org/):

```
tipo(escopo): descrição curta

Descrição detalhada opcional.

Footer opcional.
```

**Tipos:**
- `feat`: Nova feature
- `fix`: Correção de bug
- `docs`: Documentação
- `style`: Formatação, espaços
- `refactor`: Refatoração de código
- `test`: Adicionar/modificar testes
- `chore`: Tarefas de manutenção

**Exemplos:**

```bash
feat(agents): adiciona Biography Agent
fix(scraping): corrige timeout em next_matches
docs(readme): atualiza instruções de instalação
refactor(rag): melhora performance do reranker
test(chatbot): adiciona testes unitários
```

### Pull Requests

**Título:** Use o mesmo padrão de commits

**Descrição:** Inclua:

```markdown
## Descrição
Breve descrição das mudanças.

## Tipo de Mudança
- [ ] Bug fix
- [ ] Nova feature
- [ ] Breaking change
- [ ] Documentação

## Checklist
- [ ] Código segue padrões do projeto
- [ ] Testes adicionados/atualizados
- [ ] Documentação atualizada
- [ ] Todos os testes passam
- [ ] Sem conflitos com main

## Screenshots (se aplicável)

## Issues Relacionadas
Closes #123
```

---

## 🐛 Reportar Bugs

### Template de Bug Report

```markdown
**Descrição do Bug**
Descrição clara e concisa do bug.

**Como Reproduzir**
Passos para reproduzir:
1. Ir para '...'
2. Clicar em '...'
3. Scroll até '...'
4. Ver erro

**Comportamento Esperado**
O que deveria acontecer.

**Screenshots**
Se aplicável, adicione screenshots.

**Ambiente:**
 - OS: [e.g. macOS 13.0]
 - Python: [e.g. 3.10.5]
 - Versão: [e.g. 3.0.1]

**Contexto Adicional**
Qualquer outra informação relevante.
```

---

## 💡 Sugerir Features

### Template de Feature Request

```markdown
**A Feature Resolve Qual Problema?**
Descrição clara do problema.

**Solução Proposta**
Descrição da solução que você gostaria.

**Alternativas Consideradas**
Outras soluções que você considerou.

**Contexto Adicional**
Qualquer outro contexto, mockups, etc.
```

---

## 🧪 Testes

### Estrutura de Testes

```
tests/
├── test_agents.py
├── test_rag_system.py
├── test_chatbot.py
├── test_scraping.py
└── conftest.py
```

### Escrever Testes

```python
import pytest
from backend.chatbot import mirobaldo_chatbot

def test_chatbot_responde_biografia():
    """Testa se chatbot responde perguntas biográficas."""
    resposta = mirobaldo_chatbot("Quem foi António Gago?")
    assert "António Gago" in resposta
    assert len(resposta) > 50

def test_chatbot_erro_query_vazia():
    """Testa tratamento de erro com query vazia."""
    with pytest.raises(ValueError):
        mirobaldo_chatbot("")
```

### Rodar Testes

```bash
# Todos os testes
pytest

# Verbose
pytest -v

# Com coverage
pytest --cov=backend --cov-report=html

# Testes específicos
pytest tests/test_chatbot.py::test_chatbot_responde_biografia
```

---

## 🎨 Estilo de Código

### Naming Conventions

```python
# Classes: PascalCase
class BiographyAgent:
    pass

# Funções/métodos: snake_case
def processar_biografia():
    pass

# Constantes: UPPER_CASE
MAX_TOKENS = 1000
DEFAULT_MODEL = "gpt-4o-mini"

# Privadas: _prefixo
def _funcao_interna():
    pass
```

### Docstrings

```python
def processar_query(query: str, contexto: Optional[dict] = None) -> str:
    """
    Processa uma query do usuário e retorna resposta.

    Args:
        query: Query do usuário em linguagem natural
        contexto: Contexto opcional da conversa anterior

    Returns:
        Resposta processada pelo sistema

    Raises:
        ValueError: Se query estiver vazia
        APIError: Se houver erro na API OpenAI

    Example:
        >>> processar_query("Quem foi António Gago?")
        "António Gago foi um jogador..."
    """
    if not query:
        raise ValueError("Query não pode estar vazia")
    # ...
```

---

## 📦 Estrutura de Arquivos

Ao adicionar novos módulos, siga a estrutura:

```python
# backend/novo_modulo.py

"""
Módulo para [descrição].

Este módulo implementa [funcionalidade].
"""

from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Constantes
TIMEOUT = 30

# Classes
class NovaClasse:
    """Descrição da classe."""

    def __init__(self, param: str):
        """Inicializa a classe."""
        self.param = param

    def metodo(self) -> str:
        """Descrição do método."""
        return self.param

# Funções
def funcao_principal() -> None:
    """Função principal do módulo."""
    logger.info("Executando função principal")
```

---

## 🔍 Code Review

### O Que Olhamos

- ✅ Código funciona conforme esperado
- ✅ Testes cobrem casos principais
- ✅ Documentação clara e completa
- ✅ Segue padrões do projeto
- ✅ Performance adequada
- ✅ Segurança (sem exposição de secrets)

### Como Dar Feedback

- **Seja construtivo**: Sugira melhorias, não apenas critique
- **Seja específico**: Aponte linhas de código exatas
- **Seja respeitoso**: Lembre que há uma pessoa do outro lado
- **Aprenda também**: Code review é oportunidade de aprendizado mútuo

---

## 🏆 Reconhecimento

Todos os contribuidores serão reconhecidos no projeto!

Adicione-se ao [CONTRIBUTORS.md](CONTRIBUTORS.md) no seu PR.

---

## 📞 Precisa de Ajuda?

- 💬 [GitHub Discussions](https://github.com/seu-usuario/mirobaldo_3.0/discussions)
- 📧 Email: seu-email@example.com
- 📚 [Documentação](docs/)

---

## 🙏 Obrigado!

Sua contribuição torna o **Mirobaldo 3.0** melhor para todos os adeptos do Farense!

**SEMPRE FARENSE!** 🦁⚽
