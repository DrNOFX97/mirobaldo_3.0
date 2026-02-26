# Próxima Sessão — Mirobaldo 3.0

## Estado actual (2026-02-26)

- **Dataset v4** pronto: `backend/training_data_lora.jsonl` — 2146 pares
  - 1664 biografias + 307 resultados de jogos + 175 classificações
- **Run 3** arquivado em `backend/lora_adapters_run3/` (loss 0.293)
- **`backend/lora_adapters/`** vazia, pronta para Run 4

---

## Passo 1 — Iniciar Run 4 (primeira coisa a fazer)

```bash
cd /Users/f.nuno/projetos/mirobaldo_3.0
source venv/bin/activate
python backend/train_lora.py
```

- Iters previstos: **1608** (~3h no Apple Silicon)
- Loss inicial esperada: ~1.5, final esperada: <0.30
- Output: `backend/lora_adapters/adapters.safetensors`
- **Atenção**: o macOS pode matar o processo em background por pressão GPU. Se parar antes de iter 200, reiniciar.

---

## Passo 2 — Testar após treino

```bash
source venv/bin/activate
python backend/test_mlx_chatbot.py
```

Testar pelo menos:
- `"Quem foi Adelmiro?"` → deve retornar bio estruturada via RAG (não LLM)
- `"Como foi a época 1994-95 do Farense?"` → resposta com posição e pontos
- `"Qual foi a maior vitória do Farense na época 2023-24?"` → resposta com score
- `"Quem foi João Gralho?"` → prosa narrativa via RAG

---

## Passo 3 — Arrancar o servidor e testar no browser

```bash
source venv/bin/activate
python backend/app.py
# Abre http://localhost:5001
```

---

## Tarefas pendentes (por ordem de prioridade)

- [ ] **Testar Run 4 no frontend** (browser, conversa real)
- [ ] **Fix cosmético**: "Retrato Histórico" aparece como nome de clube em `format_biography_as_answer()` — o padrão `## Club` apanha `## Retrato Histórico`
- [ ] Avaliar perplexidade num conjunto de validação separado
- [ ] Considerar modelo maior (7B) se alucinações persistirem sem RAG

---

## Arquitectura RAG (recordar)

Perguntas sobre jogadores **bypassam o LLM**:
1. `find_biography_for_query()` → encontra ficheiro por nome
2. `format_biography_as_answer()` → extrai factos directamente do ficheiro
3. Só usa LLM se não encontrar biografia (com `temperature=0.2`)

Perguntas gerais → `get_response_from_agent()` → MLX Qwen2.5-3B + LoRA

---

## Fix pendente: "Retrato Histórico" como clube

Em `backend/utils.py`, função `format_biography_as_answer()`, linha ~183:
```python
club_names = re.findall(r'##\s+([^:()\\n]+?)(?:\\s*[:(]|\\s*$)', bio_text, re.MULTILINE)
```
Este padrão apanha `## Retrato Histórico` como nome de clube.
**Fix**: excluir secções conhecidas como não-clube:
```python
NON_CLUB_SECTIONS = {'retrato histórico', 'retrato', 'resumo', 'carreira', 'títulos', 'biografia'}
club_names = [c for c in club_names if c.strip().lower() not in NON_CLUB_SECTIONS]
```
