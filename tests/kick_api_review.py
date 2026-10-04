"""Regression checks for new Kick VOD IDs, long durations and legacy fallback."""
from io import BytesIO
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from yt_dlp.extractor.kick import KickVODIE
from yt_dlp.networking.common import Response
from yt_dlp.networking.exceptions import HTTPError
from yt_dlp.utils import ExtractorError
from kick_vod import ClipfarmKickVODIE

video_id = '01a0eff5-9420-738b-be87-ff9e40189c4b'
url = f'https://kick.com/preme/videos/{video_id}'
response = {'video_session': {'video_title': 'Long public VOD', 'video_duration': 24180,
                             'creator_id': '106579006', 'video_stream_status': 'vod'},
            'playback_url': {'vod': 'https://example.com/master.m3u8'}}
extractor = ClipfarmKickVODIE()
with patch.object(extractor, '_download_json', return_value=response) as request, \
        patch.object(extractor, '_extract_m3u8_formats', return_value=[{'format_id': '480', 'height': 480}]) as formats, \
        patch.object(KickVODIE, '_real_extract', side_effect=AssertionError('New ID must not use the old API')):
    info = extractor._real_extract(url)
    assert info['duration'] == 24180 and not info['is_live']
    assert info['title'] == 'Long public VOD'
    assert request.call_args.args[0] == f'https://web.kick.com/api/v1/stream/{video_id}/playback'
    assert request.call_args.kwargs['impersonate']
    assert json.loads(request.call_args.kwargs['data'])['video_player'] == {'player': {}}
    assert formats.call_args.args[0] == response['playback_url']['vod']

for status in (404, 403):
    error = ExtractorError('API request failed', cause=HTTPError(Response(BytesIO(), url, {}, status=status)))
    with patch.object(extractor, '_download_json', side_effect=error), \
            patch.object(KickVODIE, '_real_extract', return_value={'id': 'legacy'}) as legacy:
        if status == 404:
            assert extractor._real_extract(url) == {'id': 'legacy'}
            legacy.assert_called_once_with(url)
        else:
            try:
                extractor._real_extract(url)
            except ExtractorError:
                pass
            else:
                raise AssertionError('Access error should be reported')
            legacy.assert_not_called()

for invalid in ({**response, 'playback_url': {}},
                {**response, 'video_session': {'video_duration': float('nan')}},
                {'data': {'type': 'not_available', 'details': 'This video is private'}}):
    with patch.object(extractor, '_download_json', return_value=invalid):
        try:
            extractor._real_extract(url)
        except ExtractorError as exc:
            assert exc.expected
        else:
            raise AssertionError('Invalid/unavailable VOD must be rejected')
print('PASS: new playback API, 6h43m duration, legacy 404 fallback and unavailable/private VOD errors.')
