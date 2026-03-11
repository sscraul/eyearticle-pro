import typer
import time
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from loguru import logger

from src.config import settings
from src.search.scholar import setup_scholar_with_antiblock, search_scholar
from src.search.semantic import search_semantic_scholar, format_semantic_scholar_results
from src.search.unpaywall import get_pdf_url_via_unpaywall
from src.search.ranker import rank_papers
from src.download.downloader import download_pdf, DownloadError
from src.download.validator import validate_pdf
from src.extract.extractor import extract_all_content
from src.llm.gemini import generate_clinical_summary
from src.output.assembler import assemble_markdown
from src.output.converter import convert_markdown

app = typer.Typer(help="OphthalmoAgent: Agente Autônomo de Pesquisa Oftalmológica")
console = Console()

def configure_logging(level: str):
    logger.remove()
    logger.add(sys.stderr, level=level)

from src.engine import run_ophthalmo_agent

@app.command()
def generate(
    disease: str = typer.Argument(..., help="Nome da doença oftalmológica (ex: 'ceratocone')"),
    format: str = typer.Option(settings.default_format, "--format", "-f", help="Formato de saída: md, html, pdf"),
    debug: bool = typer.Option(False, "--debug", help="Habilitar logs de debug")
):
    start_time = time.time()
    log_level = "DEBUG" if debug else settings.log_level
    configure_logging(log_level)
    
    console.print(Panel.fit(f"[bold cyan]OphthalmoAgent[/] - Iniciando pesquisa para: [bold yellow]{disease}[/]", border_style="cyan"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task_id = progress.add_task("[cyan]Iniciando...", total=100)
        
        def cli_callback(status_text: str, progress_value: float):
            progress.update(task_id, description=f"[cyan]{status_text}[/]", completed=progress_value)
            # Log as info for debug
            logger.info(f"Step: {status_text} ({progress_value}%)")

        try:
            result = run_ophthalmo_agent(
                disease=disease, 
                output_format=format,
                progress_callback=cli_callback
            )
            
            final_md_path = Path(result["markdown_path"])
            elapsed = time.time() - start_time
            console.print(f"\n[bold green]Concluído com sucesso em {elapsed:.1f}s![/]")
            console.print(f"📄 Resumo disponível em: [link=file://{final_md_path.resolve()}]{final_md_path.resolve()}[/link]")
            
        except Exception as e:
            progress.stop()
            logger.exception("Agent execution failed")
            console.print(f"\n[bold red]Erro fatal:[/] {e}")
            raise typer.Exit(1)

if __name__ == "__main__":
    app()
        
    # Finalização
    elapsed = time.time() - start_time
    console.print(f"\n[bold green]Concluído com sucesso em {elapsed:.1f}s![/]")
    console.print(f"📄 Resumo disponível em: [link=file://{final_md_path.resolve()}]{final_md_path.resolve()}[/link]")

if __name__ == "__main__":
    app()
