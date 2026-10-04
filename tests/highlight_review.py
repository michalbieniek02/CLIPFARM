"""Controlled selection checks; no external API calls."""
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Pipeline, ROOT, validate_clips, SCHEMA
from highlight_selection import candidate_budget, verified_hook, choose_distinct

assert candidate_budget(5, 600, 30) == 10
assert candidate_budget(20, 3600, 5) == 40
assert candidate_budget(5, 40, 30) == 1
clip = {'start': 0, 'end': 30, 'score': 90, 'title': 'Test', 'reason': 'Puenta',
        'hook_sentence': 'To jest zdanie otwierające.'}
segments = [{'start': 0, 'end': 5, 'text': 'To jest zdanie otwierające.'},
            {'start': 5, 'end': 60, 'text': 'Kontekst i samodzielna puenta.'},
            {'start': 60, 'end': 90, 'text': 'Druga historia z wyraźną puentą.'}]
assert verified_hook(clip, segments) == clip['hook_sentence']
assert verified_hook({**clip, 'hook_sentence': 'Wymyślony nagłówek'}, segments) == ''
assert validate_clips([clip], 90, 30, 60)[0]['hook_sentence'] == clip['hook_sentence']
assert validate_clips([{k: v for k, v in clip.items() if k != 'hook_sentence'}], 90, 30, 60)[0]['hook_sentence'] == ''
assert validate_clips([{**clip, 'end': float('nan')}], 90, 30, 60) == []
assert 'hook_sentence' in SCHEMA['properties']['clips']['items']['required']
alternatives = [clip, {**clip, 'start': 10, 'end': 40, 'score': 89},
                {**clip, 'start': 60, 'end': 90, 'score': 80, 'hook_sentence': 'Druga historia z wyraźną puentą.'}]
observed = []
def controlled(self, prompt, work):
    observed.append(prompt)
    return {'clips': alternatives + [{**clip, 'start': 100, 'end': 130}]}
with patch.object(Pipeline, 'model_request', controlled):
    selected = Pipeline().select(segments, 90, 2, 30, 60, 'Praktyczne porady', ROOT / 'checks/highlights')
assert [c['start'] for c in selected] == [0, 60]
assert 'do 3 kandydatów' in observed[0]
assert 'pierwszych 3 sekundach' in observed[0]
assert 'Praktyczne porady' in observed[0]
assert len(choose_distinct([clip, {**clip, 'start': 60, 'end': 90, 'score': 89}], 2)) == 1
# Later batches already use absolute source times; never add a second offset.
long = [{'start': i * 10, 'end': (i + 1) * 10, 'text': f'Zdanie numer {i}. ' + 'tekst ' * 150} for i in range(160)]
prompts = []
def late(self, prompt, work):
    prompts.append(prompt)
    return {'clips': [{'start': 1300, 'end': 1330, 'score': 95, 'title': 'Późny fragment',
                       'reason': 'Puenta', 'hook_sentence': 'Zdanie numer 130.'}]}
with patch.object(Pipeline, 'model_request', late):
    selected = Pipeline().select(long, 1600, 1, 30, 60, '', ROOT / 'checks/highlights')
assert len(prompts) > 1
assert selected[0]['start'] == 1300 and selected[0]['end'] == 1330
assert selected[0]['hook_sentence'] == 'Zdanie numer 130.'
serialized = json.loads(json.dumps({'clips': selected}, ensure_ascii=False))
assert validate_clips(serialized['clips'], 1600, 1, 1600, strict=True) == selected
print('PASS: candidate headroom, score ranking, temporal/repeated-hook dedupe, verified quotes, old projects, invalid times and absolute long-film timestamps.')
