"""
Test script for MLX-powered chatbot
"""

import logging
from chatbot import get_response_from_agent

logging.basicConfig(level=logging.INFO)

# Test 1: Simple question
print("\n=== Test 1: Simple Question ===")
response = get_response_from_agent(
    prompt="Quem foi António Gago?",
    context="António Gago foi um jogador histórico do Farense.",
    role="És um assistente sobre o Sporting Clube Farense.",
    max_length=512
)
print(f"Response:\n{response}\n")

# Test 2: Historical question
print("\n=== Test 2: Historical Question ===")
response = get_response_from_agent(
    prompt="Qual foi a maior conquista do Farense?",
    context="O Farense foi finalista da Taça de Portugal em 1990.",
    role="És um historiador especializado no Farense.",
    max_length=512
)
print(f"Response:\n{response}\n")

print("\n=== Tests completed ===")
