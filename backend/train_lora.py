"""
LoRA Fine-tuning with MLX (Phase 4)
Train Qwen2.5-3B on Farense Q&A pairs
"""

import json
import logging
from pathlib import Path
import mlx.optimizers as optim
from mlx_lm import load
from mlx_lm.tuner.trainer import TrainingArgs, train
from mlx_lm.tuner.datasets import ChatDataset, CacheDataset
from mlx_lm.tuner.utils import linear_to_lora_layers, print_trainable_parameters

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Paths relative to this file
_BACKEND_DIR  = Path(__file__).parent
TRAINING_DATA = _BACKEND_DIR / "training_data_lora.jsonl"
OUTPUT_DIR    = _BACKEND_DIR / "lora_adapters"


def load_training_data(data_file: Path):
    """Load Q&A pairs from JSONL file"""
    logger.info(f"Loading training data from {data_file}")
    data = []
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    logger.info(f"Loaded {len(data)} training examples")
    return data


def main():
    logger.info("\n" + "="*60)
    logger.info("LORA FINE-TUNING - PHASE 4")
    logger.info("="*60 + "\n")

    base_model = "mlx-community/Qwen2.5-3B-Instruct-4bit"
    logger.info(f"Base model:     {base_model}")
    logger.info(f"Training data:  {TRAINING_DATA}")
    logger.info(f"Output dir:     {OUTPUT_DIR}")

    # ── Load base model ───────────────────────────────────────────────────────
    logger.info("\n Loading base model...")
    model, tokenizer = load(base_model)
    logger.info("Model loaded")

    # ── Freeze base weights FIRST, then apply LoRA ───────────────────────────
    # Order matters: freeze → lora (lora layers get auto-unfrozen)
    model.freeze()
    lora_config = {"rank": 8, "scale": 20.0, "dropout": 0.05}
    logger.info(f"\n Applying LoRA (rank={lora_config['rank']}, scale={lora_config['scale']})...")
    linear_to_lora_layers(model, num_layers=16, config=lora_config)
    print_trainable_parameters(model)

    # ── Prepare dataset ───────────────────────────────────────────────────────
    logger.info("\n Preparing dataset...")
    data = load_training_data(TRAINING_DATA)
    dataset = CacheDataset(ChatDataset(
        data=data,
        tokenizer=tokenizer,
        mask_prompt=True,   # only compute loss on assistant replies
    ))
    logger.info(f"Dataset ready: {len(dataset)} examples")

    # ── Training config ───────────────────────────────────────────────────────
    n_examples = len(dataset)
    batch_size  = 4
    epochs      = 3
    iters       = (n_examples // batch_size) * epochs

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    args = TrainingArgs(
        batch_size=batch_size,
        iters=iters,
        steps_per_report=50,
        steps_per_eval=0,       # no validation set
        steps_per_save=200,
        max_seq_length=512,
        adapter_file=str(OUTPUT_DIR / "adapters.safetensors"),
        grad_accumulation_steps=2,
    )

    optimizer = optim.AdamW(learning_rate=1e-4, weight_decay=0.01)

    logger.info("\n Training configuration:")
    logger.info(f"   Examples:    {n_examples}")
    logger.info(f"   Batch size:  {batch_size}")
    logger.info(f"   Epochs:      {epochs}")
    logger.info(f"   Total iters: {iters}")
    logger.info(f"   LR:          1e-4")

    # ── Train ─────────────────────────────────────────────────────────────────
    logger.info("\n Starting LoRA training...")
    logger.info("="*60)

    try:
        train(
            model=model,
            optimizer=optimizer,
            train_dataset=dataset,
            args=args,
        )

        logger.info("\n" + "="*60)
        logger.info("TRAINING COMPLETE!")
        logger.info("="*60)
        logger.info(f"\n LoRA adapter saved to: {OUTPUT_DIR}")
        logger.info(" Phase 4 complete — run mlx_interface.py to test")
        return 0

    except Exception as e:
        logger.error(f"\n Training failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
