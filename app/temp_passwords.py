"""Senhas temporárias: palavra aleatória de 4–6 letras (colecção fixa)."""
from __future__ import annotations

import random

# 50 palavras simples (4–6 letras, sem acentos) — senhas temporárias
TEMP_PASSWORD_WORDS: tuple[str, ...] = (
    "casa",
    "mesa",
    "bola",
    "livro",
    "porta",
    "chave",
    "nuvem",
    "folha",
    "vento",
    "praia",
    "lago",
    "ponte",
    "campo",
    "verde",
    "azul",
    "clara",
    "forte",
    "suave",
    "doce",
    "amigo",
    "norte",
    "leste",
    "oeste",
    "manha",
    "noite",
    "tarde",
    "feira",
    "linha",
    "ponto",
    "papel",
    "caneta",
    "quadro",
    "janela",
    "telha",
    "tijolo",
    "barro",
    "areia",
    "pedra",
    "metal",
    "vidro",
    "roupa",
    "meias",
    "caixa",
    "cesto",
    "prato",
    "copo",
    "leite",
    "trigo",
    "farol",
    "navio",
)

assert len(TEMP_PASSWORD_WORDS) == 50
assert all(4 <= len(w) <= 6 and w.isalpha() and w.islower() for w in TEMP_PASSWORD_WORDS)


def generate_temp_password() -> str:
    """Devolve uma palavra aleatória da colecção (senha temporária)."""
    return random.choice(TEMP_PASSWORD_WORDS)
