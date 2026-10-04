"""Actual streaming FFmpeg progress, stop, stall recovery and measured ETA."""
from pathlib import Path
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Cancelled, Pipeline
from vod_download import DownloadProgress, run_media

logs = []
pipeline = Pipeline(logs.append)
progress = DownloadProgress(pipeline, 24180, 300, '480p30', saved_bytes=1000000)
with patch('vod_download.time.monotonic', side_effect=[10, 11, 13]):
    progress(0, 0, '')
    progress(30, 1000000, '')
    progress(90, 2000000, '')
assert 'szacuję czas' in logs[0]
assert 'pozostało około 13 min 13 s' in logs[-1], logs
assert '30.0×' in logs[-1] and 'zapisano 3.0 MB' in logs[-1]

args = [pipeline.ffmpeg(), '-hide_banner', '-re', '-f', 'lavfi', '-i',
        'testsrc2=size=320x180:rate=30:duration=3', '-c:v', 'libx264',
        '-preset', 'ultrafast', '-f', 'null', '-']
started = time.monotonic()
updates = []
run_media(pipeline, args, lambda media, size, speed: updates.append((time.monotonic() - started, media)))
assert len(updates) >= 4 and any(.05 < media < 2.5 for _, media in updates), updates
assert any(elapsed < 2 for elapsed, media in updates if media > 0), updates

def stop(media, size, speed):
    if media > 0:
        pipeline.cancel.set()
started = time.monotonic()
try:
    run_media(pipeline, args, stop)
except Cancelled:
    pass
else:
    raise AssertionError('Live cancellation was ignored')
assert time.monotonic() - started < 2.5
pipeline.cancel.clear()

slow = [pipeline.ffmpeg(), '-hide_banner', '-readrate', '.01', '-f', 'lavfi', '-i',
        'testsrc2=size=320x180:rate=30:duration=3', '-c:v', 'libx264',
        '-preset', 'ultrafast', '-f', 'null', '-']
started = time.monotonic()
try:
    run_media(pipeline, slow, lambda *args: None, stall_timeout=.7)
except RuntimeError as exc:
    assert 'Brak postępu' in str(exc), str(exc)
else:
    raise AssertionError('A stalled process must stop and allow a retry')
assert time.monotonic() - started < 8
print('PASS: byte/media updates arrive before completion, resumed ETA uses actual throughput, cancellation and stall terminate FFmpeg.')
