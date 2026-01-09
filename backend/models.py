from pydantic import BaseModel
from typing import Optional, Dict, Any

class TrainingConfig(BaseModel):
    model: str
    dataset: Optional[str]
    batchSize: int
    learningRate: float
    epochs: int
    gradientAccumulation: int
    quantization: str
    maxSeqLength: int
    framework: str = "MLX" # Default to MLX
    presets: Optional[Dict[str, Any]] = None
