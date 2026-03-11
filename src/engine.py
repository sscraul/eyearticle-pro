import time
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
from loguru import logger

from src.config import settings
from src.download.downloader import download_pdf
from src.download.validator import validate_pdf
from src.extract.extractor import extract_all_content
from src.llm.gemini import generate_clinical_summary
from src.output.converter import convert_markdown
import src.storage as storage

def run_ophthalmo_agent(
    pdf_url: str,
    disease_label: Optional[str] = None,
    output_format: str = "md", 
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> Dict[str, Any]:
    """
    Core engine to run the EyeArticle PRO via direct URL.
    :param pdf_url: Direct link to the PDF article.
    :param disease_label: Optional label for folder naming.
    :param output_format: md, html or pdf.
    :param progress_callback: Optional function(status_text, progress_percent).
    :return: Dict with results.
    """
    
    def update_progress(text: str, value: float):
        if progress_callback:
            progress_callback(text, value)
        logger.info(f"Progress: {text} ({value}%)")

    update_progress("Iniciando processamento do link...", 5)
    
    # Prepare Dir
    import hashlib
    # Generate a hash for the specific paper to allow multiple papers per area
    paper_hash = hashlib.md5(pdf_url.encode()).hexdigest()[:8]
    
    if not disease_label:
        area_name = "geral"
    else:
        area_name = disease_label.lower().replace(" ", "_")
        
    # The new safe_name includes both the area and the specific paper hash
    safe_name = f"{area_name}/{paper_hash}"
    output_dir = settings.output_dir / area_name / paper_hash
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Download
    update_progress("Baixando PDF diretamente...", 20)
    pdf_path = output_dir / "paper.pdf"
    try:
        download_pdf(pdf_url, str(pdf_path))
        if not validate_pdf(str(pdf_path)):
            raise ValueError("O arquivo baixado não é um PDF válido.")
    except Exception as e:
        logger.error(f"Download failed for {pdf_url}: {e}")
        raise ValueError(f"Não foi possível baixar o PDF: {e}")

    # 2. Extract
    update_progress("Extraindo conteúdo do PDF...", 40)
    extraction_data = extract_all_content(str(pdf_path), str(output_dir))
    
    # 3. LLM (Gemini extracts metadata + summarizes)
    update_progress("Analisando medicina e gerando resumo...", 60)
    # Note: paper_metadata is empty here as we want Gemini to extract it
    summary_md = generate_clinical_summary(
        output_dir=str(output_dir),
        text_content=extraction_data["text"],
        images_manifest=extraction_data["images"],
        paper_metadata={"pdf_url": pdf_url} # Minimal info
    )
    
    # 4. Finalizing
    update_progress("Finalizando arquivos...", 90)
    final_md_path = output_dir / "resumo.md"

    final_summary = summary_md

    # Upload to cloud storage if configured, rewriting image URLs in the markdown
    if settings.use_cloud_storage:
        update_progress("Enviando arquivos para o storage na nuvem...", 92)
        images_dir = output_dir / "images"
        image_urls: dict[str, str] = {}
        if images_dir.exists():
            image_urls = storage.upload_directory(
                str(images_dir),
                remote_prefix=f"{safe_name}/images",
            )
            # Remap keys to match markdown references: "images/fig_001.png"
            image_urls = {f"images/{k}": v for k, v in image_urls.items()}

        final_summary = storage.rewrite_markdown_image_urls(summary_md, image_urls)
        logger.info("Rewrote markdown image URLs to cloud storage public URLs")

    with open(final_md_path, "w", encoding="utf-8") as f:
        f.write(final_summary)

    if output_format != "md":
        convert_markdown(final_md_path, output_format)

    update_progress("Concluído!", 100)

    return {
        "disease": disease_label,
        "safe_name": safe_name,
        "pdf_url": pdf_url,
        "markdown_path": str(final_md_path),
        "output_dir": str(output_dir),
        "summary": final_summary,
        "images": extraction_data["images"],
        "metadata": {
            "title": "Documento Extraído via PDF",
            "authors": "Autores identificados no resumo",
            "year": "Ano no resumo"
        }
    }
