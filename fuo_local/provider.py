# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""
TODO: 这个模块中目前逻辑非常多，包括音乐目录扫描、音乐库的构建等小部分，
这些小部分理论都可以从中拆除。
"""

import logging
import os

from fuzzywuzzy import process
from feeluown.library import AbstractProvider, ProviderV2, ProviderFlags as PF
from feeluown.utils.utils import log_exectime

logger = logging.getLogger(__name__)
SOURCE = 'local'


class LocalProvider(AbstractProvider, ProviderV2):
    class meta:
        identifier = SOURCE
        name = '本地音乐'
        flags = {}

    def __init__(self):
        super().__init__()

        self._app = None

        from .db import DB

        self.db = DB('')

    def initialize(self, app):
        self._app = app

    def scan(self, config, paths, depth=3):
        exts = config.MUSIC_FORMATS
        self.db.scan(config, paths, depth, exts)
        self.db.after_scan()

    # implements SupportsSongMultiQuality protocol.
    def song_get_media(self, song, quality):
        # TODO(this_pr)
        pass

    # @route('/cover/data')
    # TODO: read audio cover

    # TODO: list artist's contributed_albums
    # TODO: list artist's albums

    @property
    def identifier(self):
        return SOURCE

    @property
    def name(self):
        return '本地音乐'

    @property
    def songs(self):
        return self.db.list_songs()

    @property
    def albums(self):
        return self.db.list_albums()

    @property
    def artists(self):
        return self.db.list_artists()

    @log_exectime
    def search(self, keyword, **kwargs):
        limit = kwargs.get('limit', 10)
        repr_song_map = dict()
        for song in self.songs:
            key = song.title + ' ' + song.artists_name
            repr_song_map[key] = song
        choices = repr_song_map.keys()
        if choices:
            result = process.extract(keyword, choices, limit=limit)
        else:
            result = []
        result_songs = []
        for each, score in result:
            # if score > 80, keyword is almost included in song key
            if score > 80:
                result_songs.append(repr_song_map[each])
        return LSearchModel(q=keyword, songs=result_songs)

    def song_get_lyric(self, song):
        return None


provider = LocalProvider()

from .models import LSearchModel  # noqa
