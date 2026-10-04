"""Kick playback API compatibility while yt-dlp's legacy VOD API returns 404.

Endpoint/schema reference: https://github.com/yt-dlp/yt-dlp/pull/17322
The player session supplies title/duration directly, including for long VODs.
"""
import json
import math
from urllib.parse import urlparse

from yt_dlp.extractor.kick import KickVODIE
from yt_dlp.networking.exceptions import HTTPError
from yt_dlp.utils import ExtractorError, url_or_none


class ClipfarmKickVODIE(KickVODIE):
    IE_NAME = 'clipfarm:kick:vod'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        try:
            playback = self._download_json(
                f'https://web.kick.com/api/v1/stream/{video_id}/playback', video_id,
                note='Odczytuję nowy adres VOD-a Kicka', impersonate=True,
                headers={'Content-Type': 'application/json', 'Origin': 'https://kick.com', 'Referer': url},
                data=json.dumps({'video_player': {'player': {}}, 'video_session': {},
                                 'user_session': {'non_personalised_ads': True}}).encode())
        except ExtractorError as exc:
            if isinstance(exc.cause, HTTPError) and exc.cause.status == 404:
                return super()._real_extract(url)
            raise
        if playback.get('data'):
            error = playback['data']
            message = error.get('details') or error.get('type') if isinstance(error, dict) else str(error)
            raise ExtractorError(message or 'Kick nie udostępnia tego nagrania.', expected=True)
        session = playback.get('video_session') or {}
        source = url_or_none((playback.get('playback_url') or {}).get('vod'))
        if not source:
            raise ExtractorError('Kick nie udostępnia pliku tego VOD-a. Sprawdź, czy jest publiczny i zakończony.', expected=True)
        duration = session.get('video_duration')
        try:
            duration = float(duration)
        except (ValueError, TypeError):
            duration = 0
        if not math.isfinite(duration) or duration <= 0:
            raise ExtractorError('Kick nie podał długości zakończonego VOD-a.', expected=True)
        headers = {'Origin': 'https://kick.com', 'Referer': url}
        return {'id': video_id, 'title': session.get('video_title') or f'Kick {video_id}',
                'duration': duration, 'channel_id': session.get('creator_id'),
                'channel': session.get('video_series') or urlparse(url).path.split('/')[1],
                'is_live': session.get('video_stream_status') == 'live',
                'http_headers': headers,
                'formats': self._extract_m3u8_formats(source, video_id, 'mp4', headers=headers)}
