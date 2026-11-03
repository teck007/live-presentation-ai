"""Paletas de color curadas para las presentaciones generadas.

Cada paleta sigue la direccion de arte editorial/minimalista del proyecto:
fondo claro base, fondo oscuro alternativo, un acento dominante y un acento
secundario puntual, siempre con contraste alto entre fondo y texto para que
la presentacion sea legible al proyectarse.
"""

import random

# Cada paleta define los roles cromaticos que el prompt de generacion necesita:
#   background      -> fondo claro base (crema / marfil / gris suave)
#   background_alt  -> fondo oscuro para slides alternas (texto blanco encima)
#   primary         -> acento dominante (titulos, kickers, elementos clave)
#   secondary       -> acento secundario puntual (acompana, no compite)
#   text            -> texto principal sobre fondo claro
#   text_alt        -> texto sobre fondo oscuro / de color
#   muted           -> subtitulos y texto secundario
PALETTES: list[dict] = [
    {
        "id": "esmeralda-editorial",
        "name": "Esmeralda Editorial",
        "background": "#FAF7F0",
        "background_alt": "#0F2E24",
        "primary": "#0E7C5B",
        "secondary": "#D6A84A",
        "text": "#1A1A1A",
        "text_alt": "#FFFFFF",
        "muted": "#6B7280",
    },
    {
        "id": "petroleo-nordico",
        "name": "Petroleo Nordico",
        "background": "#F4F7FA",
        "background_alt": "#12303F",
        "primary": "#1F5A7A",
        "secondary": "#E08E45",
        "text": "#14212B",
        "text_alt": "#FFFFFF",
        "muted": "#5E7283",
    },
    {
        "id": "borgona-editorial",
        "name": "Borgona Editorial",
        "background": "#FAF6F3",
        "background_alt": "#33151C",
        "primary": "#7A2E3B",
        "secondary": "#C9A24B",
        "text": "#221416",
        "text_alt": "#FFFFFF",
        "muted": "#7A6A6E",
    },
    {
        "id": "indigo-moderno",
        "name": "Indigo Moderno",
        "background": "#F6F5FB",
        "background_alt": "#1D1B45",
        "primary": "#3D3B8E",
        "secondary": "#E5636B",
        "text": "#1A1930",
        "text_alt": "#FFFFFF",
        "muted": "#6A6885",
    },
    {
        "id": "bosque-sereno",
        "name": "Bosque Sereno",
        "background": "#F4F8F4",
        "background_alt": "#132B1A",
        "primary": "#2D5A3D",
        "secondary": "#B88A44",
        "text": "#15241A",
        "text_alt": "#FFFFFF",
        "muted": "#5F7265",
    },
    {
        "id": "cobre-contemporaneo",
        "name": "Cobre Contemporaneo",
        "background": "#FBF7F0",
        "background_alt": "#3A1D0F",
        "primary": "#B45A2E",
        "secondary": "#2E6E65",
        "text": "#291509",
        "text_alt": "#FFFFFF",
        "muted": "#7A6A5C",
    },
    {
        "id": "cielo-nordico",
        "name": "Cielo Nordico",
        "background": "#F4F8FB",
        "background_alt": "#14344A",
        "primary": "#2E7DA6",
        "secondary": "#F2A65A",
        "text": "#12283A",
        "text_alt": "#FFFFFF",
        "muted": "#5C7486",
    },
    {
        "id": "lavanda-mistica",
        "name": "Lavanda Mistica",
        "background": "#F8F6FB",
        "background_alt": "#2A1F3D",
        "primary": "#6C4E8C",
        "secondary": "#D98324",
        "text": "#241A33",
        "text_alt": "#FFFFFF",
        "muted": "#756A85",
    },
    {
        "id": "terracota-calida",
        "name": "Terracota Calida",
        "background": "#FBF5F1",
        "background_alt": "#4A2116",
        "primary": "#C0563B",
        "secondary": "#3B6E5E",
        "text": "#2B1A12",
        "text_alt": "#FFFFFF",
        "muted": "#7E6E66",
    },
    {
        "id": "naval-clasico",
        "name": "Naval Clasico",
        "background": "#F5F6F7",
        "background_alt": "#16242D",
        "primary": "#2F4B5C",
        "secondary": "#C7A04C",
        "text": "#1A242B",
        "text_alt": "#FFFFFF",
        "muted": "#5E6B74",
    },
    {
        "id": "azafran-profundo",
        "name": "Azafran Profundo",
        "background": "#FDF9F2",
        "background_alt": "#33260D",
        "primary": "#A97B2F",
        "secondary": "#33505A",
        "text": "#2A2215",
        "text_alt": "#FFFFFF",
        "muted": "#7A7058",
    },
    {
        "id": "pizarra-menta",
        "name": "Pizarra y Menta",
        "background": "#F5F7F6",
        "background_alt": "#16312A",
        "primary": "#3E8E6E",
        "secondary": "#5B7D9E",
        "text": "#1C2623",
        "text_alt": "#FFFFFF",
        "muted": "#64706B",
    },
]


def pick_palette() -> dict:
    """Devuelve una paleta al azar de la lista curada."""
    return random.choice(PALETTES)


# IDs estables (slugs) de cada paleta, para seleccionarlas desde la API/UI.
PALETTE_IDS: list[str] = [p["id"] for p in PALETTES]

# Valores que significan "elegir al azar" (compatibles con defaults previos).
RANDOM_PALETTE_VALUES: frozenset[str] = frozenset({"aleatoria", "auto"})


def get_palette_by_id(palette_id: str | None) -> dict | None:
    """Devuelve la paleta con el id indicado, o None si no existe.

    Los valores "aleatoria", "auto" y None no corresponden a una paleta
    concreta: devuelven None para que el llamador use `pick_palette()`.
    """
    if palette_id is None:
        return None
    normalized = palette_id.strip().lower()
    if not normalized or normalized in RANDOM_PALETTE_VALUES:
        return None
    for palette in PALETTES:
        if palette.get("id") == normalized:
            return palette
    return None


def resolve_palette(palette_id: str | None) -> dict:
    """Resuelve un id de paleta a un dict de paleta concreto.

    Si el id es None, "aleatoria" o "auto" (o desconocido), devuelve una
    paleta al azar con `pick_palette()` para mantener el comportamiento
    previo por defecto.
    """
    found = get_palette_by_id(palette_id)
    return found if found is not None else pick_palette()


def format_palette_prompt(palette: dict) -> str:
    """Genera el bloque de instrucciones con los hex de la paleta asignada."""
    return f"""PALETA CROMATICA OBLIGATORIA (asignada por el sistema):
Debes construir TODA la presentacion usando exclusivamente esta paleta:
- Fondo claro base: {palette["background"]}
- Fondo oscuro alternativo (para slides alternas): {palette["background_alt"]}
- Acento principal (dominante): {palette["primary"]}
- Acento secundario (puntual): {palette["secondary"]}
- Texto principal: {palette["text"]}
- Texto sobre fondo oscuro: {palette["text_alt"]}
- Texto secundario / subtitulos: {palette["muted"]}

REGLAS:
- Usa EXACTAMENTE estos hex como base de la paleta. No los sustituyas ni inventes colores nuevos.
- Deriva todos los tonos (tints y shades) de estos valores cuando necesites variaciones.
- El acento principal debe dominar; el secundario solo acompanar de forma puntual.
- Los neutrales (blanco, gris, negro suave) estan permitidos solo para bordes, fondos y texto secundario.
- Mantén contraste alto: texto oscuro sobre fondo claro; el texto blanco va solo sobre superficies oscuras reales (scrim, tarjeta invertida o bloque de color sólido), nunca directamente sobre las ondas del visor."""