"""
models.py — Estructuras de datos compartidas entre capas
=========================================================
Define el contrato de interfaz entre la Capa 1 (Schema Linking)
y la Capa 2 (Router Agent). Todos los módulos del proyecto importan
sus tipos desde aquí para garantizar consistencia.

Autor: Daniel Camilo Blanco Galán
Universidad Nacional de Colombia
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TableInfo:
    """
    Representa una tabla del esquema SQL con sus metadatos relevantes
    para el proceso de schema linking.
    """
    name: str                          # Nombre exacto de la tabla en SQLite
    description: str                   # Descripción semántica de la tabla
    columns: list[str]                 # Lista de nombres de columnas
    primary_key: str | None = None     # Columna PK si existe
    row_count: int = 0                 # Número aproximado de filas


@dataclass
class SchemaContext:
    """
    Objeto de salida de la Capa 1 y entrada de la Capa 2.

    Encapsula toda la información necesaria para que el agente genere
    una consulta SQL o decida redirigir al retriever vectorial, sin
    necesidad de conocer el esquema completo de la BD.

    Campos
    ------
    query               Query original del usuario en lenguaje natural
    query_type          Canal determinado por el schema linker:
                          - "sql"    -> pregunta estructurada (conteo, ranking...)
                          - "rag"    -> pregunta semántica (similitud, temas...)
                          - "hybrid" -> requiere SQL + recuperación vectorial
    relevant_tables     Nombres de las tablas seleccionadas por MMR
    relevant_columns    Diccionario {tabla: [columnas relevantes]}
    foreign_keys        Lista de FKs relevantes como strings descriptivos
                        Ej.: ["ArticleAuthor.SR -> Article.SR"]
    entities            Entidades detectadas por NER {tipo: valor}
                        Ej.: {"author": "Robledo", "year": "2020"}
    confidence          Confianza del proceso de schema linking (0.0 - 1.0)
    """
    query: str
    query_type: Literal["sql", "rag", "hybrid"]
    relevant_tables: list[str]
    relevant_columns: dict[str, list[str]]
    foreign_keys: list[str]
    entities: dict[str, str]
    confidence: float

    def to_prompt_string(self) -> str:
        """
        Serializa el contexto a un bloque de texto listo para inyectar
        en el prompt del LLM.
        """
        lines: list[str] = []
        lines.append(f"-- Query del usuario: {self.query}")
        lines.append(f"-- Canal: {self.query_type}  |  Confianza: {self.confidence:.2f}")
        lines.append("")
        lines.append("-- TABLAS RELEVANTES:")
        for table in self.relevant_tables:
            cols = self.relevant_columns.get(table, [])
            lines.append(f"  {table}({', '.join(cols)})")
        if self.foreign_keys:
            lines.append("")
            lines.append("-- RELACIONES FK:")
            for fk in self.foreign_keys:
                lines.append(f"  {fk}")
        if self.entities:
            lines.append("")
            lines.append("-- ENTIDADES DETECTADAS:")
            for tipo, valor in self.entities.items():
                lines.append(f"  {tipo}: {valor}")
        return "\n".join(lines)

    def is_sql_query(self) -> bool:
        return self.query_type in ("sql", "hybrid")

    def is_rag_query(self) -> bool:
        return self.query_type in ("rag", "hybrid")
