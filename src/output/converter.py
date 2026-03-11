import subprocess
from loguru import logger
from pathlib import Path

def convert_markdown(md_path: Path, format: str) -> None:
    """
    Converts the generated Markdown to HTML or PDF using pandoc.
    """
    if format not in ["html", "pdf"]:
        logger.warning(f"Unsupported format: {format}")
        return
        
    output_ext = f".{format}"
    out_path = md_path.with_suffix(output_ext)
    
    logger.info(f"Converting Markdown to {format.upper()}...")
    
    try:
        # Requires pandoc installed on the system
        cmd = ["pandoc", str(md_path), "-o", str(out_path)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Successfully converted to {out_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Pandoc conversion failed: {e.stderr}")
    except FileNotFoundError:
        logger.error("Pandoc is not installed or not in PATH. Cannot convert.")
