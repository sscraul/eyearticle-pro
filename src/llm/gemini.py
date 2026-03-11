import json
import base64
from pathlib import Path
from loguru import logger
from typing import Dict, Any, List

from google import genai
from google.genai import types

from src.config import settings
from .prompts import SYSTEM_PROMPT, CORRECTIVE_PROMPT
from .validator import validate_summary_structure

def encode_image_base64(filepath: Path) -> str:
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def generate_clinical_summary(output_dir: str, text_content: List[Dict[str, Any]], images_manifest: List[Dict[str, Any]], paper_metadata: Dict[str, Any]) -> str:
    """
    Generates the clinical summary using Gemini 2.0 Flash.
    Sends the text and all related images inside the prompt.
    Validates output structure and retries if necessary.
    """
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY config is required to generate the summary.")
        
    client = genai.Client(api_key=settings.gemini_api_key)
    
    # Compile the text content
    full_text = "\n\n".join([f"--- Page {p['page']} ---\n{p['text']}" for p in text_content])
    
    # Format the images manifest
    manifest_str = "Lista de imagens e a sintaxe Markdown que VOCÊ DEVE usar:\n"
    for img in images_manifest:
        manifest_str += f"- ID: {img['id']} | Legenda: '{img['caption']}' | Sintaxe: `![{img['caption']}]({img['path']})`\n"
        
    paper_url = paper_metadata.get("pdf_url", "N/A")

    prompt = SYSTEM_PROMPT.format(
        paper_url=paper_url,
        images_manifest=manifest_str, 
        article_text=full_text
    )
    
    # Prepare multimodal payload parts
    contents = [prompt]
    
    # Add actual images as inline data
    base_dir = Path(output_dir)
    for img in images_manifest:
        try:
            img_path = base_dir / img["path"]
            if img_path.exists():
                logger.debug(f"Attaching image {img_path} to payload")
                img_data = img_path.read_bytes()
                mime_type = "image/png"
                if str(img_path).lower().endswith(".jpeg") or str(img_path).lower().endswith(".jpg"):
                    mime_type = "image/jpeg"
                contents.append(
                    types.Part.from_bytes(data=img_data, mime_type=mime_type)
                )
        except Exception as e:
            logger.warning(f"Failed to load image part for LLM: {e}")

    # Generate first attempt
    model_name = "gemini-2.5-flash" 
    logger.info("Sending prompt to Gemini...")
    response = client.models.generate_content(
        model=model_name,
        contents=contents
    )
    
    summary = response.text
    
    # Validation Loop
    max_retries = 2
    for attempt in range(max_retries):
        if validate_summary_structure(summary):
            return summary
            
        logger.warning(f"Validation failed (Attempt {attempt+1}/{max_retries}). Retrying with corrective prompt.")
        corrective_p = CORRECTIVE_PROMPT.format(previous_summary=summary)
        
        # In the retry, we don't need to resend images, just the corrective conversation.
        # But we pass the updated text intent.
        retry_contents = [
            prompt,
            types.Part.from_text(text="Model Output: " + summary),
            types.Part.from_text(text=corrective_p)
        ]
        
        response = client.models.generate_content(
            model=model_name,
            contents=retry_contents
        )
        summary = response.text
        
    logger.error("Failed to generate a valid summary after max retries.")
    return summary
