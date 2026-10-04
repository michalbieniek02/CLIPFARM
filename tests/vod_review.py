"""Real HTTP HLS download, CPU encoding, resume and MP4 join; no external network."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Pipeline, Cancelled
from vod_download import timestamp, kick_url, video_url, download_vod, QUALITIES, format_selector

assert timestamp('01:02:03') == 3723
for value in ('nan', '-1', '00:60:00'):
    try:
        timestamp(value)
    except ValueError:
        pass
    else:
        raise AssertionError(value)
try:
    kick_url('https://example.com/videos/123')
except ValueError:
    pass
else:
    raise AssertionError('Non-Kick URLs must be rejected')
for url, provider in [('https://youtu.be/test', 'YouTube'), ('https://youtube.com/shorts/test', 'YouTube'),
                      ('https://twitch.tv/videos/123', 'Twitch'), ('https://clips.twitch.tv/test', 'Twitch'),
                      ('https://x.com/test/status/123', 'X'), ('https://twitter.com/test/status/123', 'X')]:
    assert video_url(url)[1] == provider
try:
    video_url('https://youtu.be/test', 'Twitch')
except ValueError:
    pass
else:
    raise AssertionError('Explicit provider mismatch must be rejected')
assert 'bv+ba' in format_selector('Oryginał')

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def copyfile(self, source, output):
        try:
            super().copyfile(source, output)
        except (ConnectionResetError, BrokenPipeError):
            pass

checks = Path(__file__).resolve().parents[1] / 'checks'
checks.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=checks) as temporary:
    root = Path(temporary)
    pipeline = Pipeline()
    pipeline.run([pipeline.ffmpeg(), '-hide_banner', '-y', '-f', 'lavfi', '-i',
        'testsrc2=size=1280x720:rate=60:duration=12', '-f', 'lavfi', '-i',
        'sine=frequency=440:sample_rate=48000:duration=12', '-c:v', 'libx264',
        '-preset', 'ultrafast', '-g', '120', '-c:a', 'aac', '-f', 'hls', '-hls_time', '2',
        '-hls_list_size', '0', str(root / 'source.m3u8')])
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    def resolver(_):
        return {'title': 'Local VOD test', 'duration': 12, 'url': f'http://127.0.0.1:{server.server_port}/source.m3u8'}
    saved = []
    def interrupt(message):
        if 'zapisano część 1/' in message:
            pipeline.cancel.set()
    pipeline.log = interrupt
    try:
        with patch('vod_download.CHUNK', 5):
            try:
                download_vod(pipeline, 'https://kick.com/test/videos/123', root / 'out', gpu=False, resolver=resolver)
            except Cancelled:
                pass
            else:
                raise AssertionError('Cancellation was ignored')
            assert len(list((root / 'out').glob('.vod-*/*.ts'))) == 1
            pipeline.cancel.clear()
            pipeline.log = saved.append
            output = download_vod(pipeline, 'https://kick.com/test/videos/123', root / 'out', gpu=False, resolver=resolver)
            metadata = pipeline.probe(output)
            assert metadata['height'] == 480 and metadata['audio']
            assert abs(metadata['duration'] - 12) < 1
            assert any('zachowuję część 1/' in line for line in saved)
            import av
            with av.open(str(output)) as container:
                stream = container.streams.video[0]
                print('Video timing:', stream.base_rate, stream.average_rate, metadata['duration'])
                assert float(stream.base_rate) == 30
                assert abs(float(stream.average_rate) - 30) < .3
            # Every requested compression setting produces its actual canvas/FPS.
            for quality, profile in QUALITIES.items():
                if profile is None or quality == '480p30':
                    continue
                output = download_vod(pipeline, 'https://youtube.com/watch?v=test', root / 'out',
                                      end=3, gpu=False, resolver=resolver, quality=quality, provider='YouTube')
                assert pipeline.probe(output)['height'] == profile[0]
                with av.open(str(output)) as container:
                    assert float(container.streams.video[0].base_rate) == profile[1]
            # Separate video/audio URLs, as returned for higher-quality YouTube.
            def split_resolver(_):
                info = resolver(_)
                return {**info, 'requested_formats': [
                    {'url': info['url'], 'vcodec': 'h264', 'acodec': 'none'},
                    {'url': info['url'], 'vcodec': 'none', 'acodec': 'aac'}]}
            split = download_vod(pipeline, 'https://youtube.com/watch?v=split', root / 'out',
                                 end=3, gpu=False, resolver=split_resolver, quality='720p60')
            assert pipeline.probe(split)['audio']
            def original_resolver(_):
                return {**resolver(_), 'id': 'test-original', 'ext': 'mp4', 'format_id': 'test',
                        'protocol': 'm3u8_native', 'extractor': 'generic', 'extractor_key': 'Generic'}
            original = download_vod(pipeline, 'https://x.com/test/status/123', root / 'out',
                                    resolver=original_resolver, quality='Oryginał', provider='X')
            assert pipeline.probe(original)['height'] == 720
            with av.open(str(original)) as container:
                assert float(container.streams.video[0].base_rate) == 60
            def original_split_resolver(_):
                info = original_resolver(_)
                return {**info, 'format_id': 'video+audio', 'ext': 'mkv',
                        'protocol': 'm3u8_native+m3u8_native', 'requested_formats': [
                    {**info, 'format_id': 'video', 'vcodec': 'h264', 'acodec': 'none'},
                    {**info, 'format_id': 'audio', 'vcodec': 'none', 'acodec': 'aac'}]}
            merged_original = download_vod(pipeline, 'https://youtube.com/watch?v=original-split', root / 'out',
                                          resolver=original_split_resolver, quality='Oryginał')
            assert merged_original.suffix == '.mkv'
            assert pipeline.probe(merged_original)['height'] == 720
            assert pipeline.probe(merged_original)['audio']
    finally:
        server.shutdown()
        server.server_close()
print('PASS: four compression profiles, original 720p60, separate A/V streams, cancellation/resume, provider and time validation.')
