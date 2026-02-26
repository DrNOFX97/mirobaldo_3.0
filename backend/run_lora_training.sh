#!/bin/bash
# LoRA Fine-tuning Script - Phase 4

echo "======================================"
echo "LORA FINE-TUNING - PHASE 4"
echo "======================================"
echo ""

# Configuration
MODEL="mlx-community/Qwen2.5-3B-Instruct-4bit"
DATA_DIR="training_data"
OUTPUT_DIR="lora_adapters"
ITERS=500  # Start with 500 iterations
BATCH_SIZE=1
LEARNING_RATE=1e-5
STEPS_PER_REPORT=10
STEPS_PER_EVAL=50
SAVE_EVERY=100

echo "Configuration:"
echo "  Model: $MODEL"
echo "  Data: $DATA_DIR"
echo "  Output: $OUTPUT_DIR"
echo "  Iterations: $ITERS"
echo "  Batch size: $BATCH_SIZE"
echo "  Learning rate: $LEARNING_RATE"
echo ""

# Activate venv
source ../venv/bin/activate

# Run training
echo "Starting LoRA training..."
echo "======================================"
echo ""

mlx_lm.lora \
    --model "$MODEL" \
    --train \
    --data "$DATA_DIR" \
    --fine-tune-type lora \
    --batch-size $BATCH_SIZE \
    --iters $ITERS \
    --learning-rate $LEARNING_RATE \
    --steps-per-report $STEPS_PER_REPORT \
    --steps-per-eval $STEPS_PER_EVAL \
    --save-every $SAVE_EVERY \
    --adapter-path "$OUTPUT_DIR" \
    --grad-checkpoint

echo ""
echo "======================================"
echo "Training complete!"
echo "LoRA adapter saved to: $OUTPUT_DIR"
echo "======================================"
