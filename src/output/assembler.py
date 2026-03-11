import os
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from typing import Dict, Any

TEMPLATE_DIR = Path(__file__).parent / "templates"

def assemble_markdown(
    disease: str, 
    paper_metadata: Dict[str, Any], 
    llm_summary: str,
    output_path: Path
) -> None:
    """
    Assembles the final markdown using Jinja2 templates.
    """
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("resumo.md.j2")
    
    # We parse the paper metadata to fill out variables in Jinja
    content = template.render(
        disease=disease.title(),
        title=paper_metadata.get("title", "Desconhecido"),
        authors=", ".join(paper_metadata.get("authors", [])) if isinstance(paper_metadata.get("authors"), list) else paper_metadata.get("authors", "Desconhecido"),
        year=paper_metadata.get("year", "Desconhecido"),
        doi=paper_metadata.get("doi", "N/A"),
        pdf_url=paper_metadata.get("pdf_url", "N/A"),
        summary=llm_summary
    )
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
