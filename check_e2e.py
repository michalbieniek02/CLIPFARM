from engine import Pipeline, ROOT
import json

p = Pipeline(print)
work = ROOT / 'checks' / 'e2e'
work.mkdir(parents=True, exist_ok=True)
source = work / 'narrated.mp4'
p.run([p.ffmpeg(), '-y', '-f', 'lavfi', '-i', 'testsrc2=size=640x360:rate=25',
       '-i', str(ROOT / 'checks' / 'speech.wav'), '-shortest', '-c:v', 'libx264',
       '-preset', 'ultrafast', '-c:a', 'aac', str(source)])
metadata = p.probe(source)
segments = p.transcribe(source, work, 'small', device='cuda')
clips = p.select(segments, metadata['duration'], 1, 30, 60,
                 'Praktyczna rada o tworzeniu filmów z pełną puentą.', work)
files = p.export(source, clips, segments, work / 'exports', True, True, 'nvenc')
(work / 'result.json').write_text(json.dumps({'clips': clips, 'files': files}, ensure_ascii=False, indent=2), encoding='utf-8')
print('PASS: full GPU transcription → GPT 6.1 Sol → vertical NVENC export with captions')
