"""
World Visualization – brand "Midnight & Coral".

Costanti del brand per la nuova cartella del progetto.
Se il motore di aperidata usa nomi diversi in brand/theme.py,
rinomina queste costanti in modo che corrispondano.
"""

from pathlib import Path

# --- Identità -----------------------------------------------------------
BRAND_NAME = "World Visualization"
BRAND_SHORT = "WorldViz"
HANDLE = "@worldvisualization"  # aggiorna con l'handle definitivo

# --- Colori -------------------------------------------------------------
MIDNIGHT = "#0E1A2B"   # sfondo principale, testo su fondo chiaro
CORAL = "#FF6B5B"      # accento: il dato chiave, una sola cosa per slide
MIST = "#E9EEF3"       # testo e bolle su fondo scuro
PAPER = "#F3F1EC"      # sfondo chiaro alternativo
RING = "#2A3A52"       # linee sottili, griglie, cornici su fondo scuro
MUTED_DARK = "#8C9AAD"  # testo secondario su Midnight (fonti, note)
MUTED_LIGHT = "#4A5566" # testo secondario su Paper

BG = MIDNIGHT
FG = MIST
ACCENT = CORAL

# Serie per grafici con più categorie: il corallo resta riservato al dato chiave.
SERIES = ["#E9EEF3", "#7FA7D9", "#4C6E9E", "#2A3A52"]
HIGHLIGHT = CORAL

# --- Tipografia ---------------------------------------------------------
# Manrope (Google Fonts, licenza OFL): https://fonts.google.com/specimen/Manrope
FONT_FAMILY = "Manrope"
FONT_WEIGHT_TITLE = 800   # ExtraBold
FONT_WEIGHT_BODY = 400    # Regular
FONT_WEIGHT_LABEL = 600   # SemiBold

# --- Asset ----------------------------------------------------------------
ASSETS = Path(__file__).parent / "assets"
LOGO_MARK_DARK = ASSETS / "mark_dark-bg.svg"
LOGO_MARK_LIGHT = ASSETS / "mark_light-bg.svg"
LOGO_MARK_SMALL_DARK = ASSETS / "mark_simple_dark-bg.svg"   # sotto ~120 px
LOGO_MARK_SMALL_LIGHT = ASSETS / "mark_simple_light-bg.svg"
LOGO_LOCKUP_DARK = ASSETS / "lockup_dark_transparent.svg"
LOGO_LOCKUP_LIGHT = ASSETS / "lockup_light.svg"
WORDMARK_SHORT_DARK = ASSETS / "wordmark_worldviz_dark-bg.svg"
AVATAR = ASSETS / "avatar_instagram.png"
