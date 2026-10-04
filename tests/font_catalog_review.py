"""All bundled faces must render in Pillow, Qt and real FFmpeg/libass."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tempfile

from PIL import ImageFont
from PySide6.QtGui import QGuiApplication, QFontDatabase

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import Pipeline
from font_catalog import FONT_DIR, FONT_FILES, FONT_NAMES, font_path, resolve_font

assert len(FONT_NAMES) == len(set(FONT_NAMES)) == 20
assert resolve_font('  mOnTsErRaT ') == 'Montserrat'
for unknown in ('../outside.ttf', 'C:/Windows/Fonts/arial.ttf', '', None, 'unknown'):
    assert resolve_font(unknown) == 'Anton'
    assert font_path(unknown) == font_path('Anton')

provenance = json.loads((FONT_DIR / 'provenance.json').read_text(encoding='utf-8'))
records = {record['family']: record for record in provenance['fonts']}
assert set(records) == set(FONT_NAMES)
app = QGuiApplication.instance() or QGuiApplication([])
metrics = set()
for family in FONT_NAMES:
    path = font_path(family)
    assert path.is_relative_to(FONT_DIR) and path.is_file()
    record = records[family]
    assert record['file'] == FONT_FILES[family]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
    license_text = (ROOT / record['license']).read_text(encoding='utf-8')
    assert 'SIL OPEN FONT LICENSE' in license_text.upper(), family
    font = ImageFont.truetype(str(path), 84)
    assert font.getname()[0] == family, (family, font.getname())
    try:
        font.get_variation_axes()
    except OSError:
        pass
    else:
        raise AssertionError(f'{family}: fixed caption face required')
    missing = bytes(font.getmask('\u0378'))
    for char in 'ĄĆĘŁŃÓŚŹŻąćęłńóśźż':
        assert bytes(font.getmask(char)) != missing, (family, char)
    metrics.add(round(font.getlength('ŻÓŁW I SZYBKI KLIP'), 2))
    font_id = QFontDatabase.addApplicationFont(str(path))
    assert font_id >= 0 and family in QFontDatabase.applicationFontFamilies(font_id), family
assert len(metrics) >= 18, 'The options must use distinct real faces'

styles = '\n'.join(
    f'Style: F{i},{family},32,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,'
    '0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1'
    for i, family in enumerate(FONT_NAMES))
events = '\n'.join(
    f'Dialogue: 0,0:00:00.00,0:00:01.00,F{i},,0,0,0,,'
    f'{{\\pos(360,{40 + 50 * i})}}{family}: ŻÓŁW ĄĆĘŁŃÓŚŹŻ'
    for i, family in enumerate(FONT_NAMES))
ass = f'''[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1080
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles}
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{events}
'''
(ROOT / 'checks').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='font-catalog-', dir=ROOT / 'checks') as temp:
    target = Path(temp) / 'all-fonts.ass'
    target.write_text(ass, encoding='utf-8-sig')
    relative = target.relative_to(ROOT).as_posix()
    result = subprocess.run([
        Pipeline.ffmpeg(), '-hide_banner', '-f', 'lavfi', '-i', 'color=black:s=720x1080:d=0.1',
        '-vf', f'ass={relative}:fontsdir=assets/fonts', '-frames:v', '1', '-f', 'null', '-'],
        cwd=ROOT, text=True, encoding='utf-8', errors='replace', capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    for family in FONT_NAMES:
        selection = re.search(r'fontselect: \(' + re.escape(family) + r', [^\n]+', result.stderr)
        assert selection, f'{family} was not selected by libass:\n{result.stderr}'
        selected = selection.group(0).split('->', 1)[-1].split(',', 1)[0]
        compact = re.sub(r'[^a-z]', '', family.casefold())
        assert compact in re.sub(r'[^a-z]', '', selected.casefold()), (family, selection.group(0))
        assert 'failed' not in selection.group(0).casefold()

print('PASS: 20 licensed fixed TTFs, Polish glyphs, Pillow, Qt and real libass font selection')
