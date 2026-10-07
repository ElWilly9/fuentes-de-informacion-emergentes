"""
ingestion_service.py — Servicio de Orquestación de Ingesta
==========================================================
Coordina la carga de datos desde un archivo Excel hacia la base de datos
SQL y el índice vectorial ChromaDB, proporcionando feedback a la UI.
"""

from pathlib import Path
from typing import Callable, Optional
from src.ingestion.load_db import load_excel
from src.layer3_rag.embedder import index_abstracts

class IngestionService:
    """
    Servicio que encapsula el proceso de preparación de un corpus.
    Permite el seguimiento del progreso mediante un callback.
    """

    def __init__(self, base_sessions_dir: Path):
        self.base_sessions_dir = base_sessions_dir

    def prepare_corpus(
        self,
        corpus_name: str,
        xlsx_file: Path,
        progress_callback: Callable[[str, float], None]
    ) -> tuple[Path, Path]:
        """
        Ejecuta la pipeline completa:
        1. Crear carpetas de sesión.
        2. Ingesta SQL.
        3. Indexación Vectorial.

        Retorna la ruta de la BD y la ruta de ChromaDB.
        """
        # 1. Definir rutas de la sesión
        session_dir = self.base_sessions_dir / corpus_name
        raw_dir = session_dir / "raw"
        db_dir = session_dir / "db"
        chroma_dir = session_dir / "chroma"

        # Crear estructura de carpetas
        raw_dir.mkdir(parents=True, exist_ok=True)
        db_dir.mkdir(parents=True, exist_ok=True)
        chroma_dir.mkdir(parents=True, exist_ok=True)

        # El archivo ya ha sido guardado en raw_dir por la UI,
        # no es necesario copiarlo nuevamente.
        dest_xlsx = xlsx_file

        # 2. Ingesta SQL
        db_path = db_dir / "bibliometria.db"
        load_excel(
            xlsx_path=dest_xlsx,
            db_path=db_path,
            progress_callback=progress_callback
        )

        # 3. Indexación Vectorial
        index_abstracts(
            db_path=db_path,
            chroma_dir=chroma_dir,
            progress_callback=progress_callback
        )

        return db_path, chroma_dir
