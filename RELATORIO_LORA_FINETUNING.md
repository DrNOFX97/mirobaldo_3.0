# Relatório: Fine-Tuning LoRA do Mirobaldo 3.0

**Data:** 2026-02-25
**Modelo base:** `mlx-community/Qwen2.5-3B-Instruct-4bit`
**Framework:** MLX (Apple Silicon)
**Técnica:** LoRA (Low-Rank Adaptation)

---

## 1. Arquitectura do Pipeline

```
Dados brutos (214 ficheiros de biografias)
        ↓
Phase 3: generate_qa_pairs.py
  - deduplicação por nome (208 jogadores únicos)
  - síntese de markdown estruturado vs prosa
        ↓
training_data_lora.jsonl (1664 pares Q&A — dataset v3)
        ↓
Phase 4: train_lora.py
        ↓
lora_adapters/ (adapters.safetensors)
        ↓
mlx_interface.py (inferência local)
        ↓
chatbot.py (integração com RAG)
```

---

## 2. Geração de Dados de Treino (Phase 3)

### Ficheiro: `backend/generate_qa_pairs.py`

#### Problema (versão anterior)
As respostas usavam o **texto completo da biografia** como `assistant` content. Resultado:
- Respostas de 800–1200 palavras com markdown estruturado
- O modelo aprendeu a gerar listas infinitas de bullet points
- Loop de repetição após ~500 tokens gerados

#### Solução implementada
**`summarize_biography(text, max_words=300)`**
- Remove headers markdown (`# Título`)
- Remove bold/italic (`**texto**`)
- Remove links e bullets
- Extrai os primeiros 3 parágrafos de prosa limpa
- Limita a 300 palavras

**Respostas diferenciadas por tipo de pergunta:**

| Pergunta | Resposta | Parágrafos | ~Palavras |
|----------|----------|-----------|-----------|
| "Quem foi X?" | Intro | 1 | ~80 |
| "Podes apresentar X?" | Intro | 1 | ~80 |
| "Conta-me sobre X." | Overview | 2 | ~150 |
| "Fala-me de X." | Overview | 2 | ~150 |
| "Qual foi a carreira de X?" | Detail | 3 | ~250 |
| "O que fez X pelo Farense?" | Detail | 3 | ~250 |
| "Quais foram as conquistas de X?" | Detail | 3 | ~250 |
| "Quando jogou X?" | Overview | 2 | ~150 |

#### Estatísticas do dataset (v3)
- **Total de pares Q&A:** 1664
- **Jogadores únicos:** 208 (214 ficheiros, 6 duplicatas removidas)
- **Média de tokens por exemplo:** 75 palavras
- **Total de tokens:** 124,898

#### Estatísticas do dataset (v4 — versão actual)
- **Total de pares Q&A:** 2146 (+29% vs v3)
  - Biografias: 1664
  - Resultados de jogos: 307 (91 épocas, 1933-34 → 2024-25)
  - Classificações: 175 (83 épocas + milestones)
- **Média de tokens por exemplo:** 72 palavras
- **Total de tokens:** 155,580

#### Problemas encontrados nas versões anteriores do dataset

**Problema v1 → v2: `_is_structured_markdown` demasiado permissivo**
- Classificava ficheiros .md narrativos (com múltiplos `##` headers e bullets) como "structured"
- `_synthesize_from_markdown` tentava extrair metadados (data de nascimento, clubes, títulos)
- Quando não havia metadados estruturados, extraía **apenas os títulos 🏆** como resposta
- Resultado: 105 exemplos com "Conquistou N título(s):" como resposta a "Quem foi X?" e "Quando jogou X?"

**Solução v3:** `_is_structured_markdown` agora exige o padrão `**DD/MM/YYYY, Lugar** | **Posição**` — apenas ficheiros com metadata header real são tratados como "structured". Os restantes .md são processados como prosa.

**Problema v2: Duplicatas de jogadores com stems diferentes**
- O mesmo jogador tinha 2-3 ficheiros (ex: `bio_antonio_gago.txt`, `antonio_gago.md`, `bio_antonio_gago_formatado.md`)
- A deduplicação por stem não era suficiente
- Resultado: António Gago com 24 exemplos contraditórios (3 formatos de resposta para a mesma pergunta)

**Solução v3:** Deduplicação por **nome do jogador extraído**. Para cada nome único, mantém o ficheiro com maior `prose_score` (contagem de caracteres não-markdown). António Gago passou de 24 → 8 exemplos.

**Problema v3 (residual): Títulos de secção como primeiro parágrafo**
- Após strip de `# `, "António Guerreiro da Silva Gago: O Sócio Nº1..." ficava como primeiro "parágrafo"
- Filtro corrigido: parágrafos devem ter ≥8 palavras E conter pontuação de fim de frase (`.!?;`)

---

## 3. Treino LoRA (Phase 4)

### Ficheiro: `backend/train_lora.py`

#### Problemas encontrados e correcções

**Erro 1: `TrainingArgs` incompatível**
- O `train_lora.py` original usava parâmetros inexistentes (`num_epochs`, `lora_rank`, `adapter_path`, etc.)
- `TrainingArgs` real: `batch_size`, `iters`, `steps_per_report`, `steps_per_eval`, `steps_per_save`, `max_seq_length`, `adapter_file`, `grad_accumulation_steps`

**Erro 2: `train()` sem optimizer**
- A função `train()` exige `optimizer` como argumento
- Adicionado: `optim.AdamW(learning_rate=1e-4, weight_decay=0.01)`

**Erro 3: `KeyError: 0` no dataset**
- `ChatDataset.__getitem__` devolve o dict raw, não tokens
- `CacheDataset` é o wrapper que aplica `.process()` e tokeniza
- Correcção: `CacheDataset(ChatDataset(...))`

**Erro 4: `[QuantizedMatmul::vjp] no gradient wrt quantized weights`**
- Ordem errada: LoRA era aplicado ANTES de `model.freeze()`
- As camadas LoRA ficavam re-congeladas pelo `freeze()`
- **Ordem correcta:** `model.freeze()` → `linear_to_lora_layers()` (que auto-descongela os parâmetros LoRA)

#### Configuração de treino

```python
# LoRA
lora_config = {"rank": 8, "scale": 20.0, "dropout": 0.05}
num_layers = 16  # últimas 16 camadas do transformer

# TrainingArgs
batch_size  = 4
iters       = (n_examples // 4) * 3   # 3 épocas
max_seq_length = 512
grad_accumulation_steps = 2

# Optimizer
AdamW(learning_rate=1e-4, weight_decay=0.01)
```

#### Resultados dos 3 runs de treino

| Run | Dataset | Exemplos | Iters | Loss inicial | Loss final | Notas |
|-----|---------|---------|-------|-------------|-----------|-------|
| 1   | v1 (prosa apenas) | 1704 | 1278 | 2.122 | 0.311 | Respostas demasiado longas nos dados |
| 2   | v2 (prosa + síntese markdown) | 1616 | 1212 | 1.184 | 0.295 | 105 exemplos contraditórios, 53 jogadores com formato conflituante |
| 3   | v3 (dataset corrigido) | 1664 | 1248 | 1.545 | **0.293** | 0 exemplos contraditórios, deduplicação por nome ✅ |

**Curva de loss do Run 3:**

| Iter | Loss | Notas |
|------|------|-------|
| 50   | 1.545 | |
| 100  | 1.342 | |
| 150  | 1.265 | |
| 200  | 1.099 | checkpoint salvo |
| 250  | 1.069 | |
| 300  | 1.001 | |
| 350  | 0.871 | |
| 400  | 0.951 | checkpoint salvo |
| 450  | 0.608 | queda abrupta |
| 500  | 0.590 | |
| 600  | ~0.55 | checkpoint salvo |
| 650  | 0.538 | |
| 700  | 0.536 | |
| 750  | 0.529 | |
| 950  | 0.323 | |
| 1000 | 0.324 | checkpoint salvo |
| 1050 | 0.286 | |
| 1100 | 0.317 | |
| 1150 | 0.293 | |
| 1248 | **0.293** | final |

**Nota Run 3:** Erro Metal GPU `kIOGPUCommandBufferCallbackErrorImpactingInteractivity` na primeira tentativa (após Iter 50) — macOS terminou processo background por pressão GPU. Segunda tentativa completou com sucesso.

---

## 4. Inferência (mlx_interface.py)

### Problemas encontrados e correcções

**Problema 1: Loop de repetição**
- O `_format_messages` fazia o template ChatML manualmente
- O tokenizer nativo (`apply_chat_template`) é mais correcto
- Adicionado: `make_repetition_penalty(1.4)` como logits processor

**Problema 2: `generate()` sem sampler**
- A API real usa `sampler` (não `temp`/`top_p` directamente)
- Correcção: `make_sampler(temp=0.7, top_p=0.9)`

**Configuração final:**
```python
MLXInterface(
    model_name="mlx-community/Qwen2.5-3B-Instruct-4bit",
    adapter_path="backend/lora_adapters",   # auto-detectado
)

chat_completion(
    messages=...,
    max_tokens=1024,
    temperature=0.7,
    top_p=0.9,
    repetition_penalty=1.4,
)
```

---

## 5. Integração no Chatbot

### `chatbot.py`
- Já importa `chat_completion_mlx` do `mlx_interface.py` ✅
- Usa RAG para injectar contexto antes da geração ✅
- O `llm_interface.py` (legado do Mistral) não é usado pelo chatbot principal ✅

### Fluxo de uma pergunta:
```
User: "Quem foi António Gago?"
        ↓
chatbot.py: detect keyword "gago"
        ↓
get_antonio_gago_biography() → retorna biografia estruturada
        ↓
generate_rich_response() → narrativa hard-coded (fallback rápido)

Para perguntas gerais:
        ↓
find_relevant_context() → RAG busca contexto relevante
        ↓
get_response_from_agent(prompt, context, role)
        ↓
chat_completion_mlx(messages, max_tokens=1024)
        ↓
MLXInterface → Qwen2.5-3B + LoRA adapters → resposta
```

---

## 6. Resultados de Qualidade

### Sem contexto RAG (base model, sem fine-tuning)
> "António Gago foi um avançado brasileiro nascido em 1973 em São Paulo..." ❌

### Com adapters LoRA Run 2 (sem contexto RAG)
> "Conquistou 2 título(s): Títulos nacionais em Marrocos; Finalista da Taça dos Campeões Europeus..." ❌
> (dataset v2 com exemplos contraditórios — modelo confuso)

### Com adapters LoRA Run 3 (sem contexto RAG)
> "António Gago nasceu a 28/07/1933 em Faro e foi Avançado." ❌
> (formato correcto, mas factos alucinados — esperado: 3B params não memorizam 208 jogadores)

### Com adapters LoRA Run 3 + contexto RAG
> "António Gago nasceu a 27/09/1897 em Faro e foi um dos sócios fundadores do Sporting Clube Farense." ✅
> (data e facto correctos — o modelo usa o contexto injectado)

### Via chatbot.py completo (hard-coded + RAG + LoRA)
> Narrativa histórica longa, factualmente correcta, prosa natural, sem loop ✅

### Conclusão sobre o papel do LoRA
O fine-tuning com LoRA **não serve para memorizar factos** num modelo de 3B params (apenas 0.216% de parâmetros treináveis). O seu papel real é:
- Ensinar o **estilo de resposta** em português europeu
- Ensinar o **tom** do Mirobaldo (assistente do Farense)
- Reduzir alucinações em **contexto histórico genérico**
- Melhorar a capacidade de **usar contexto RAG injectado** correctamente

Os factos específicos (datas, clubes, posições) devem sempre ser fornecidos via **RAG**.

---

## 7. Próximos Passos

- [x] ~~Retreinar com dataset melhorado (v3 — dataset corrigido)~~ ✅ Run 3 completo
- [x] ~~Implementar `generate_results_questions()`~~ ✅ 307 pares, 91 épocas
- [x] ~~Implementar `generate_classification_questions()`~~ ✅ 175 pares, 83 épocas

### Run 4 — Pronto para iniciar

```bash
source venv/bin/activate
python backend/train_lora.py
```

Configuração prevista:
- Dataset: `training_data_lora.jsonl` (2146 exemplos — dataset v4)
- Iters: 1608 (2146 // 4 × 3 épocas)
- Adapters anteriores (Run 3) arquivados em: `backend/lora_adapters_run3/`
- Output: `backend/lora_adapters/`

### Tarefas pendentes após Run 4
- [ ] Avaliar perplexidade num conjunto de validação separado
- [ ] Testar no frontend (browser)
- [ ] Considerar modelo maior (7B) se alucinações sem RAG forem problemáticas

---

## 8. Ficheiros Chave

| Ficheiro | Função |
|----------|--------|
| `backend/generate_qa_pairs.py` | Gera training_data_lora.jsonl |
| `backend/training_data_lora.jsonl` | Dataset de treino v3 (1664 pares, 208 jogadores únicos) |
| `backend/train_lora.py` | Script de treino LoRA |
| `backend/lora_adapters/` | Adapters treinados |
| `backend/mlx_interface.py` | Inferência local com Qwen2.5 |
| `backend/chatbot.py` | Chatbot principal (usa mlx_interface) |
| `backend/llm_interface.py` | Legado (mock Mistral, não usado) |
