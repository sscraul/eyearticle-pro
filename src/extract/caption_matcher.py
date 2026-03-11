import re

def find_caption(page_text: str, page_num: int, img_id: int) -> str:
    """
    Finds a caption using regex for common patterns in medical articles.
    """
    patterns = [
        r'(Fig(?:ure|\.)\s*\d+[.:]\s*[^\n]+)',
        r'(Figura\s*\d+[.:]\s*[^\n]+)',
        r'(Image\s*\d+[.:]\s*[^\n]+)',
        r'(Imagem\s*\d+[.:]\s*[^\n]+)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, page_text, re.IGNORECASE)
        if matches:
            return matches[0].strip()
            
    return f"Imagem {img_id} (página {page_num +1})"

def has_figure_indicators(text: str) -> bool:
    """Detects if the page likely contains figures or images."""
    return bool(re.search(
        r'(Fig\.|Figure|Figura|Image|Imagem)\s*\d+',
        text, re.IGNORECASE
    ))
