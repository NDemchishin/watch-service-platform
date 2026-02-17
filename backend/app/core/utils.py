"""
Утилиты приложения.
"""
import re


def sanitize_text(text: str | None, max_length: int = 1000) -> str | None:
    """Очистить текст от управляющих символов и ограничить длину."""
    if text is None:
        return None
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text[:max_length].strip()
