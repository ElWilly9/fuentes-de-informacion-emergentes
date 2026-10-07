"""
ner_extractor.py — Extracción de entidades desde la query del usuario
=====================================================================
Detecta entidades relevantes para el sistema bibliométrico en una query
en lenguaje natural en español. Combina dos estrategias:

  1. spaCy NER: detecta personas (autores), organizaciones (instituciones),
     fechas y lugares.
  2. Reglas personalizadas: detecta patrones bibliométricos específicos
     como años, cuartiles (Q1-Q4), tipos de documento, clasificaciones
     Tree of Science (root/trunk/leaf) y países comunes.

Salida: dict {tipo_entidad: valor} que se incluye en SchemaContext.entities

Uso:
    python src/layer1_schema/ner_extractor.py --query "autores colombianos sobre innovacion"
    python src/layer1_schema/ner_extractor.py --query "journals Q1 entre 2018 y 2022"

Autor: Daniel Camilo Blanco Galán — Universidad Nacional de Colombia
"""

import argparse
import re
from typing import Any

import spacy
from spacy.language import Language

# ─────────────────────────────────────────────────────────────────────────────
# Carga del modelo spaCy (singleton para no recargarlo en cada llamada)
# ─────────────────────────────────────────────────────────────────────────────

_nlp: Language | None = None

def _get_nlp() -> Language:
    """Carga el modelo spaCy la primera vez y lo reutiliza después."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("es_core_news_sm")
        except OSError:
            raise RuntimeError(
                "Modelo spaCy no encontrado. "
                "Ejecuta: python -m spacy download es_core_news_sm"
            )
    return _nlp


# ─────────────────────────────────────────────────────────────────────────────
# Patrones de reglas bibliométricas
# ─────────────────────────────────────────────────────────────────────────────

# Años: 4 dígitos entre 1900 y 2099
PATTERN_YEAR = re.compile(r"\b(19\d{2}|20\d{2})\b")

# Rango de años: "entre 2010 y 2020", "2010-2020", "de 2010 a 2020"
PATTERN_YEAR_RANGE = re.compile(
    r"\b(19\d{2}|20\d{2})\s*(?:[-–]|y|a|hasta)\s*(19\d{2}|20\d{2})\b"
)

# Cuartiles Scimago
PATTERN_QUARTILE = re.compile(r"\bQ([1-4])\b", re.IGNORECASE)

# Tipos de documento
PATTERN_DOCTYPE = re.compile(
    r"\b(article|review|conference paper|book chapter|editorial|"
    r"articulo|revision|capitulo|conferencia)\b",
    re.IGNORECASE
)

# Clasificación Tree of Science
PATTERN_TOS = re.compile(
    r"\b(root|trunk|leaf|raiz|raíz|tronco|hoja|fundacional(?:es)?|"
    r"frontera|estructural(?:es)?)\b",
    re.IGNORECASE
)

# Países más frecuentes en el corpus (nombres en español e inglés)
PATTERN_COUNTRY = re.compile(
    r"\b(colombia|colombian(?:o|a|os|as)?|"
    r"estados unidos|united states|usa|"
    r"reino unido|united kingdom|uk|"
    r"australia|australian?|"
    r"canada|canadian?|"
    r"españa|spain|spanish|"
    r"china|chinese|"
    r"alemania|germany|german|"
    r"brasil|brazil|brazilian?|"
    r"india|indian|"
    r"italia|italy|italian?|"
    r"francia|france|french)\b",
    re.IGNORECASE
)

# Intención de ranking / top-N
PATTERN_TOPN = re.compile(
    r"\b(?:top|los|las|primeros?|mejores?)\s+(\d+)\b",
    re.IGNORECASE
)

# Palabras clave de intención
INTENT_KEYWORDS = {
    "ranking":    r"\b(m[aá]s\s+citad[oa]s?|mayor\s+impacto|top|ranking|prolífico|prolífico)\b",
    "temporal":   r"\b(tendencia|evoluci[oó]n|por\s+a[nñ]o|temporal|crecimiento)\b",
    "semantic":   r"\b(hablan?\s+de|sobre|trat[ae]n?\s+de|relacionad[oa]s?\s+con|temas?)\b",
    "network":    r"\b(colaboraci[oó]n|coautor[ií]a|red\s+de|network|conexi[oó]n)\b",
    "foundation": r"\b(fundacional|seminal|base|origen|tree\s+of\s+science|raíz|root)\b",
}


# ─────────────────────────────────────────────────────────────────────────────
# Extractor principal
# ─────────────────────────────────────────────────────────────────────────────

def extract_entities(query: str) -> dict[str, Any]:
    """
    Extrae entidades bibliométricas de una query en lenguaje natural.

    Combina NER de spaCy con reglas regex específicas del dominio.

    Parámetros
    ----------
    query : str
        Pregunta del usuario en español.

    Retorna
    -------
    dict
        Diccionario con entidades detectadas. Las claves posibles son:
          - "author"      : nombre de autor detectado
          - "year"        : año único (ej: "2020")
          - "year_range"  : rango de años (ej: "2018-2022")
          - "quartile"    : cuartil (ej: "Q1")
          - "doc_type"    : tipo de documento (ej: "review")
          - "tos_class"   : clasificación ToS (ej: "root")
          - "country"     : país (ej: "Colombia")
          - "top_n"       : número para ranking (ej: "5")
          - "intent"      : intención detectada (ej: "ranking")
          - "institution" : institución detectada por spaCy
    """
    entities: dict[str, Any] = {}
    nlp = _get_nlp()
    doc = nlp(query)

    # ── 1. spaCy NER ──────────────────────────────────────────────────────────
    for ent in doc.ents:
        label = ent.label_
        text  = ent.text.strip()

        if label == "PER" and "author" not in entities:
            # Persona → probablemente un autor
            entities["author"] = text

        elif label == "ORG" and "institution" not in entities:
            # Organización → institución o revista
            entities["institution"] = text
            

    # ── 2. Reglas regex ───────────────────────────────────────────────────────

    # Rango de años (tiene precedencia sobre año único)
    m = PATTERN_YEAR_RANGE.search(query)
    if m:
        entities["year_range"] = f"{m.group(1)}-{m.group(2)}"
    else:
        # Año único (tomar el primero que aparezca)
        m = PATTERN_YEAR.search(query)
        if m:
            entities["year"] = m.group(0)

    # Cuartil
    m = PATTERN_QUARTILE.search(query)
    if m:
        entities["quartile"] = f"Q{m.group(1)}"

    # Tipo de documento
    m = PATTERN_DOCTYPE.search(query)
    if m:
        entities["doc_type"] = m.group(0).lower()

    # Tree of Science
    m = PATTERN_TOS.search(query)
    if m:
        raw = m.group(0).lower()
        # Normalizar a los valores de la BD: root / trunk / leaf
        tos_map = {
            "root": "root", "raiz": "root", "raíz": "root",
            "fundacional": "root", "fundacionales": "root",
            "trunk": "trunk", "tronco": "trunk", "estructural": "trunk",
            "estructurales": "trunk",
            "leaf": "leaf", "hoja": "leaf", "frontera": "leaf",
        }
        entities["tos_class"] = tos_map.get(raw, raw)

    # País (reglas regex tienen precedencia sobre spaCy para países)
    m = PATTERN_COUNTRY.search(query)
    if m:
        raw = m.group(0).lower()
        # Normalizar a código/nombre estándar
        country_map = {
            "colombia": "Colombia",
            "colombiano": "Colombia", "colombiana": "Colombia",
            "colombianos": "Colombia", "colombianas": "Colombia",
            "estados unidos": "United States", "united states": "United States",
            "usa": "United States",
            "reino unido": "United Kingdom", "united kingdom": "United Kingdom",
            "uk": "United Kingdom",
            "australia": "Australia", "australian": "Australia",
            "australia": "Australia",
            "canada": "Canada", "canadian": "Canada",
            "españa": "Spain", "spain": "Spain", "spanish": "Spain",
            "china": "China", "chinese": "China",
            "alemania": "Germany", "germany": "Germany", "german": "Germany",
            "brasil": "Brazil", "brazil": "Brazil", "brazilian": "Brazil",
            "india": "India", "indian": "India",
            "italia": "Italy", "italy": "Italy", "italian": "Italy",
            "francia": "France", "france": "France", "french": "France",
        }
        entities["country"] = country_map.get(raw, raw.title())

    # Top-N
    m = PATTERN_TOPN.search(query)
    if m:
        entities["top_n"] = m.group(1)

    # ── 3. Intención ─────────────────────────────────────────────────────────
    for intent_name, pattern in INTENT_KEYWORDS.items():
        if re.search(pattern, query, re.IGNORECASE):
            entities["intent"] = intent_name
            break   # tomar la primera intención detectada

    return entities


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extrae entidades bibliométricas de una query en español"
    )
    parser.add_argument(
        "--query", type=str, required=True,
        help="Query en lenguaje natural"
    )
    args = parser.parse_args()

    print(f"\nQuery: {args.query}")
    print("-" * 50)
    entidades = extract_entities(args.query)

    if entidades:
        for clave, valor in entidades.items():
            print(f"  {clave:<15}: {valor}")
    else:
        print("  (no se detectaron entidades)")
