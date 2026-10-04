"""Real local HLS: native copy, two encoders, retries, cancellation, resume and failure cleanup."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys
import tempfile
import threading
import time
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Pipeline, ROOT, Cancelled
from vod_download import download_vod, matches_profile, run_media, transcode_args

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
    def copyfile(self, source, output):
        try: super().copyfile(source, output)
        except (ConnectionResetError, BrokenPipeError): pass

(ROOT / 'checks').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=ROOT / 'checks') as directory:
    root = Path(directory)
    p = Pipeline()
    p.run([p.ffmpeg(), '-hide_banner', '-y', '-f', 'lavfi', '-i',
           'testsrc2=size=852x480:rate=30:duration=12', '-f', 'lavfi', '-i',
           'sine=frequency=440:sample_rate=48000:duration=12', '-c:v', 'libx264',
           '-preset', 'ultrafast', '-b:v', '1200k', '-g', '60', '-c:a', 'aac', '-b:a', '96k',
           '-f', 'hls', '-hls_time', '2', '-hls_list_size', '0', str(root / 'sample.m3u8')])
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    info = {'id': 'sample', 'title': 'Real local sample', 'duration': 12, 'width': 852,
            'height': 480, 'fps': 30, 'tbr': 1296, 'vcodec': 'h264', 'acodec': 'aac',
            'protocol': 'm3u8_native', 'ext': 'mp4', 'format_id': '480p',
            'extractor': 'generic', 'extractor_key': 'Generic',
            'url': f'http://127.0.0.1:{server.server_port}/sample.m3u8'}
    try:
        assert matches_profile(info, '480p30')
        assert not matches_profile({**info, 'height': 720}, '480p30')
        assert not matches_profile({**info, 'fps': 60}, '480p30')
        assert not matches_profile({**info, 'tbr': 3000}, '480p30')
        assert not matches_profile({**info, 'tbr': None}, '480p30')
        assert not matches_profile({**info, 'vcodec': 'hevc'}, '480p30')
        events = []
        p.log = events.append
        copied = download_vod(p, 'https://kick.com/test/videos/123', root / 'native', resolver=lambda _: dict(info))
        assert any('bez ponownego kodowania' in line for line in events)
        assert copied.suffix == '.mp4' and p.probe(copied)['audio']
        def frame_hashes(source):
            data, _ = p.run([p.ffmpeg(), '-hide_banner', '-i', str(source), '-map', '0:v:0', '-f', 'framemd5', '-'])
            return [line.rsplit(',', 1)[-1].strip() for line in data.splitlines() if line and not line.startswith('#')]
        assert frame_hashes(root / 'sample.m3u8') == frame_hashes(copied), 'Native profile copy must preserve every decoded frame'
        active, peak = [0], [0]
        gate = threading.Lock()
        failed_once = set()
        def cpu_args(ffmpeg, current, start, length, output, gpu, quality):
            return transcode_args(ffmpeg, current, start, length, output, False, quality)
        def measured_run(pipeline, args, progress, **kwargs):
            name = Path(args[-1]).name
            with gate:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            try:
                if name == '00001.partial.ts' and name not in failed_once:
                    failed_once.add(name)
                    raise RuntimeError('Temporary connection failure')
                return run_media(pipeline, args, progress, **kwargs)
            finally:
                with gate: active[0] -= 1
        # Partial ranges require encoding; real CPU FFmpeg substitutes only for
        # the CI runner's absent NVIDIA hardware, while the parallel scheduler is real.
        with patch('vod_download.CHUNK', 3), patch('vod_download.transcode_args', side_effect=cpu_args), patch('vod_download.run_media', side_effect=measured_run):
            def interrupted(line):
                events.append(line)
                if 'zapisano część' in line: p.cancel.set()
            p.log = interrupted
            try:
                download_vod(p, 'https://kick.com/test/videos/123', root / 'parallel', end=9,
                             resolver=lambda _: dict(info), gpu=True)
            except Cancelled:
                pass
            else:
                raise AssertionError('Parallel cancellation must stop the job')
            assert active[0] == 0 and peak[0] == 2
            assert list((root / 'parallel').glob('.vod-*/*.ts'))
            p.cancel.clear()
            events.clear()
            p.log = events.append
            resumed = download_vod(p, 'https://kick.com/test/videos/123', root / 'parallel', end=9,
                                   resolver=lambda _: dict(info), gpu=True)
            assert any('zachowuję część' in line for line in events)
            metadata = p.probe(resumed)
            assert abs(metadata['duration'] - 9) < 1 and metadata['audio'] and metadata['height'] == 480
            values = [float(match[1]) for line in events if (match := re.search(r'VOD: ([\d.]+) /', line))]
            assert values == sorted(values), values
            assert any('zapisano' in line and 'MB' in line for line in events)
        def fail_run(pipeline, args, progress, **kwargs):
            if Path(args[-1]).name == '00001.partial.ts':
                raise RuntimeError('Connection unavailable')
            return run_media(pipeline, args, progress, **kwargs)
        with patch('vod_download.CHUNK', 3), patch('vod_download.transcode_args', side_effect=cpu_args), patch('vod_download.run_media', side_effect=fail_run):
            started = time.monotonic()
            try:
                download_vod(p, 'https://kick.com/test/videos/123', root / 'failure', end=9,
                             resolver=lambda _: dict(info), gpu=True)
            except RuntimeError as exc:
                assert '3 próbach' in str(exc)
            else:
                raise AssertionError('Failed parts must fail the whole job')
            assert time.monotonic() - started < 8
            assert not list((root / 'failure').glob('*.mp4'))
    finally:
        p.cancel.clear()
        server.shutdown()
        server.server_close()
print('PASS: native HLS frame hashes preserved; two actual FFmpeg workers; retry, cancellation/resume, monotonic progress and failed-job cleanup.')
