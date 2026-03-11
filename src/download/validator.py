import fitz  # PyMuPDF
from loguru import logger

def validate_pdf(file_path: str) -> bool:
    """
    Validates that a downloaded file is a valid PDF.
    Checks for the %PDF- header and ensures PyMuPDF can open it and it has >= 1 page.
    """
    logger.info(f"Validating PDF: {file_path}")
    
    # 1. Header check
    try:
        with open(file_path, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                logger.error("File does not have a valid PDF header.")
                return False
    except FileNotFoundError:
        logger.error("File not found.")
        return False
        
    # 2. PyMuPDF integrity check
    try:
        doc = fitz.open(file_path)
        if doc.page_count < 1:
            logger.error("PDF has 0 pages.")
            doc.close()
            return False
            
        doc.close()
        logger.info("PDF validated successfully.")
        return True
    except Exception as e:
        logger.error(f"PyMuPDF failed to open the file: {e}")
        return False
