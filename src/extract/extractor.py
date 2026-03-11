import fitz  # PyMuPDF
import json
import os
from loguru import logger
from typing import Dict, Any, Tuple
from pathlib import Path

from .caption_matcher import find_caption, has_figure_indicators

def extract_all_content(pdf_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Extracts text and ALL images from a medical PDF.
    Returns a dictionary with page text and images manifest.
    """
    logger.info(f"Extracting content from {pdf_path}")
    doc = fitz.open(pdf_path)
    all_text = []
    images_manifest = []
    img_counter = 0

    # Ensure output directory for images exists
    images_dir = Path(output_dir) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    for page_num, page in enumerate(doc):
        # 1. TEXT EXTRACTION
        text_dict = page.get_text("dict")
        page_text = page.get_text("text")
        
        all_text.append({
            "page": page_num + 1,
            "text": page_text,
            "blocks": text_dict.get("blocks", [])
        })

        # 2. IMAGE EXTRACTION (Primary method)
        image_list = page.get_images(full=True)
        images_found_on_page = False

        for img_info in image_list:
            xref = img_info[0]

            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                width = base_image["width"]
                height = base_image["height"]

                # Filter out very small images (e.g., icons, bullets)
                if width < 100 or height < 100:
                    continue

                images_found_on_page = True
                img_counter += 1
                filename = f"fig_{img_counter:03d}.{image_ext}"
                filepath = images_dir / filename

                with open(filepath, "wb") as f:
                    f.write(image_bytes)

                caption = find_caption(page_text, page_num, img_counter)

                images_manifest.append({
                    "id": img_counter,
                    "page": page_num + 1,
                    "path": f"images/{filename}", # Relative path for markdown
                    "caption": caption,
                    "width": width,
                    "height": height,
                    "format": image_ext
                })

            except Exception as e:
                logger.warning(f"Failed to extract image xref {xref}: {e}")
                pass

        # 3. FALLBACK: Full page rendering
        # For complex vector figures that aren't captured as embedded images
        if not images_found_on_page and has_figure_indicators(page_text):
            logger.info(f"Rendering full page {page_num + 1} due to unextracted figures.")
            try:
                pix = page.get_pixmap(dpi=300)
                img_counter += 1
                filename = f"page_{page_num+1}_full.png"
                filepath = images_dir / filename
                pix.save(filepath)

                images_manifest.append({
                    "id": img_counter,
                    "page": page_num + 1,
                    "path": f"images/{filename}",
                    "caption": f"Página {page_num+1} renderizada (contém figuras)",
                    "width": pix.width,
                    "height": pix.height,
                    "format": "png"
                })
            except Exception as e:
                logger.error(f"Error rendering page {page_num + 1}: {e}")

    # Generate Manifest
    manifest_path = Path(output_dir) / "images_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(images_manifest, f, indent=2, ensure_ascii=False)

    doc.close()
    
    # Return structure matching PRD
    return {"text": all_text, "images": images_manifest}
