import re
from loguru import logger

REQUIRED_SECTIONS = [
    r'(?i)##\s*1\.?\s*Introdu[cç][aã]o',
    r'(?i)##\s*2\.?\s*Epidemiologia',
    r'(?i)##\s*3\.?\s*Diagn[oó]stico',
    r'(?i)##\s*4\.?\s*Exames',
    r'(?i)##\s*5\.?\s*Tratamento',
    r'(?i)##\s*6\.?\s*Progn[oó]stico',
    r'(?i)##\s*7\.?\s*Acompanhamento'
]

def validate_summary_structure(summary_md: str) -> bool:
    """
    Validates that the generated summary contains all 7 required sections.
    """
    missing_sections = []
    
    for idx, pattern in enumerate(REQUIRED_SECTIONS, start=1):
        if not re.search(pattern, summary_md):
            missing_sections.append(idx)
            
    if missing_sections:
        logger.warning(f"Summary is missing sections: {missing_sections}")
        return False
        
    logger.info("Summary passed structure validation (all 7 sections present).")
    return True
