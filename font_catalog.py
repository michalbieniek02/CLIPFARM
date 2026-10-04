"""Bundled caption faces shared by the editor, text measurement and libass.

Every face is a fixed TrueType font with its upstream license bundled.
Source URLs and checksums are recorded in assets/fonts/provenance.json.
"""
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
FONT_DIR = PROJECT_ROOT / 'assets' / 'fonts'
FONT_FILES = {
    'Anton': 'assets/fonts/Anton-Regular.ttf',
    'Bebas Neue': 'assets/fonts/BebasNeue-Regular.ttf',
    'Montserrat': 'assets/fonts/Montserrat-Bold.ttf',
    'Poppins': 'assets/fonts/Poppins-Bold.ttf',
    'Inter': 'assets/fonts/Inter-Bold.ttf',
    'Roboto': 'assets/fonts/Roboto-Bold.ttf',
    'Oswald': 'assets/fonts/Oswald-Bold.ttf',
    'Open Sans': 'assets/fonts/OpenSans-Bold.ttf',
    'Lato': 'assets/fonts/Lato-Bold.ttf',
    'Nunito': 'assets/fonts/Nunito-Bold.ttf',
    'Rubik': 'assets/fonts/Rubik-Bold.ttf',
    'Barlow Condensed': 'assets/fonts/BarlowCondensed-Bold.ttf',
    'Archivo Black': 'assets/fonts/ArchivoBlack-Regular.ttf',
    'DM Sans': 'assets/fonts/DMSans-Bold.ttf',
    'Fjalla One': 'assets/fonts/FjallaOne-Regular.ttf',
    'Raleway': 'assets/fonts/Raleway-Bold.ttf',
    'Quicksand': 'assets/fonts/Quicksand-Bold.ttf',
    'Lobster': 'assets/fonts/Lobster-Regular.ttf',
    'Pacifico': 'assets/fonts/Pacifico-Regular.ttf',
    'Bungee': 'assets/fonts/Bungee-Regular.ttf',
}
FONT_NAMES = tuple(FONT_FILES)
_NAMES = {name.casefold(): name for name in FONT_NAMES}


def resolve_font(name):
    """Return a known family; old projects and unknown input retain Anton."""
    return _NAMES.get(str(name or '').strip().casefold(), 'Anton')


def font_path(name):
    """Return a bundled file, never an arbitrary path supplied by a project."""
    return PROJECT_ROOT / FONT_FILES[resolve_font(name)]
