"""
MLX Interface for Local LLM Inference
Replaces OpenAI API with MLX + Qwen2.5-3B (fine-tuned with LoRA)
"""

import logging
import os
from typing import Optional, List, Dict
import mlx.core as mx
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_repetition_penalty, make_sampler

logger = logging.getLogger(__name__)

# Path to LoRA adapters, relative to this file
_ADAPTER_PATH = os.path.join(os.path.dirname(__file__), "lora_adapters")

class MLXInterface:
    """
    Wrapper for MLX-based local LLM inference.
    Compatible with OpenAI-style chat completions API.
    """

    def __init__(
        self,
        model_name: str = "mlx-community/Qwen2.5-3B-Instruct-4bit",
        adapter_path: Optional[str] = _ADAPTER_PATH,
    ):
        """
        Initialize MLX model.

        Args:
            model_name: HuggingFace model identifier
            adapter_path: Path to LoRA adapters directory (None to skip)
        """
        self.model_name = model_name
        self.adapter_path = adapter_path if (adapter_path and os.path.isdir(adapter_path)) else None
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        """Load MLX model and tokenizer, with LoRA adapters if available"""
        try:
            if self.adapter_path:
                logger.info(f"Loading MLX model: {self.model_name} + adapters from {self.adapter_path}")
                self.model, self.tokenizer = load(self.model_name, adapter_path=self.adapter_path)
                logger.info("MLX model + LoRA adapters loaded successfully")
            else:
                logger.info(f"Loading MLX model: {self.model_name} (no adapters)")
                self.model, self.tokenizer = load(self.model_name)
                logger.info("MLX model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load MLX model: {e}")
            raise

    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Format chat messages using the tokenizer's native chat template.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Formatted prompt string
        """
        if hasattr(self.tokenizer, "apply_chat_template"):
            return self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

        # Fallback: manual ChatML format
        formatted = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                formatted += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role == "user":
                formatted += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                formatted += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        formatted += "<|im_start|>assistant\n"
        return formatted

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        repetition_penalty: float = 1.4,
    ) -> str:
        """
        Generate chat completion using MLX.

        Args:
            messages: List of message dicts (OpenAI format)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            repetition_penalty: Penalty for repeated tokens (>1.0 reduces repetition)

        Returns:
            Generated response text
        """
        try:
            # Format messages
            prompt = self._format_messages(messages)

            # Build sampler and logits processors
            sampler = make_sampler(temp=temperature, top_p=top_p)
            logits_processors = [make_repetition_penalty(repetition_penalty)] if repetition_penalty != 1.0 else None

            # Generate response
            logger.debug(f"Generating with prompt length: {len(prompt)}")
            response = generate(
                model=self.model,
                tokenizer=self.tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                verbose=False,
                sampler=sampler,
                logits_processors=logits_processors,
            )

            # Clean up response (remove prompt echo)
            response = response.strip()

            # Remove the <|im_end|> token if present
            if "<|im_end|>" in response:
                response = response.split("<|im_end|>")[0].strip()

            logger.debug(f"Generated response length: {len(response)}")
            return response

        except Exception as e:
            logger.error(f"MLX generation error: {e}")
            return "Desculpe, não consegui processar sua pergunta no momento."


# Global MLX instance (lazy loaded)
_mlx_instance: Optional[MLXInterface] = None


def get_mlx_instance(adapter_path: Optional[str] = _ADAPTER_PATH) -> MLXInterface:
    """Get or create global MLX instance (singleton pattern)"""
    global _mlx_instance
    if _mlx_instance is None:
        _mlx_instance = MLXInterface(adapter_path=adapter_path)
    return _mlx_instance


def chat_completion_mlx(
    messages: List[Dict[str, str]],
    max_tokens: int = 1024,
    temperature: float = 0.7,
    **kwargs
) -> str:
    """
    Convenience function for chat completion.
    Compatible with OpenAI API style.

    Args:
        messages: List of message dicts
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature

    Returns:
        Generated response text
    """
    mlx = get_mlx_instance()
    return mlx.chat_completion(messages, max_tokens, temperature)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    mlx = get_mlx_instance()
    using_adapters = "COM adapters LoRA" if mlx.adapter_path else "SEM adapters (modelo base)"
    print(f"\nModelo carregado: {using_adapters}")

    messages = [
        {"role": "system", "content": "És o Mirobaldo, assistente especializado na história do Sporting Clube Farense."},
        {"role": "user", "content": "Quem foi António Gago?"}
    ]

    response = chat_completion_mlx(messages)
    print(f"\nResponse:\n{response}")
