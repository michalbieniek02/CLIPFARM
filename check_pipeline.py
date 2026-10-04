"""Small integration checks with a generated film; no user media is touched."""
import json
from pathlib import Path
from engine import Pipeline, ROOT, subtitle_text, validate_clips

def main():
    pipeline = Pipeline(print)
    work = ROOT / 'checks'
    work.mkdir(exist_ok=True)
    source = work / 'synthetic.mp4'
    pipeline.run([pipeline.ffmpeg(), '-y', '-f', 'lavfi', '-i', 'testsrc2=size=640x360:rate=25',
                  '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100',
                  '-t', '8', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(source)])
    assert Pipeline.probe(source)['audio']
    assert validate_clips([{'start': -1, 'end': 4}, {'start': 0, 'end': float('nan')}], 8, 1, 8) == []
    segments = [{'start': 0, 'end': 3, 'text': 'Próba napisów: zażółć gęślą jaźń.'},
                {'start': 3, 'end': 8, 'text': 'To jest drugi fragment.'}]
    subtitles = subtitle_text(segments, 2, 5)
    assert '00:00:00,000 --> 00:00:01,000' in subtitles
    assert '00:00:01,000 --> 00:00:03,000' in subtitles
    clips = [{'start': 2, 'end': 5, 'title': 'Test eksportu', 'score': 90, 'reason': 'Materiał syntetyczny.'}]
    files = pipeline.export(source, clips, segments, work / 'export', vertical=True, burn=True, encoder='nvenc')
    metadata = pipeline.probe(files[0])
    assert (metadata['width'], metadata['height']) == (1080, 1920), metadata
    assert abs(metadata['duration'] - 3) < .2, metadata
    import av
    with av.open(files[0]) as container:
        frame = next(container.decode(video=0))
        frame.to_image().save(work / 'export-frame.png')
    (work / 'verification.json').write_text(json.dumps(metadata, indent=2))
    print('PASS: NVENC, 9:16, 3s, audio, subtitles, invalid clip rejection.')

if __name__ == '__main__':
    main()
