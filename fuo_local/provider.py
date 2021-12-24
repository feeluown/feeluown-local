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

from feeluown.utils import aio
from feeluown.utils.utils import log_exectime
from feeluown.media import Media, MediaType
from feeluown.models import reverse
from feeluown.models import ModelType, SearchType

from .utils import read_audio_cover

logger = logging.getLogger(__name__)
SOURCE = 'local'


def scan_directory(directory, exts=None, depth=2):
    exts = exts or ['mp3', 'fuo']
    if depth < 0:
        return []

    media_files = []
    if not os.path.exists(directory):
        return []
    for path in os.listdir(directory):
        path = os.path.join(directory, path)
        if os.path.isdir(path):
            files = scan_directory(path, exts, depth - 1)
            media_files.extend(files)
        elif os.path.isfile(path):
            if path.split('.')[-1] in exts:
                media_files.append(path)
    return media_files


class Library:
    def __init__(self):
        self._songs = {}
        self._albums = {}
        self._artists = {}

    def list_songs(self):
        return list(self._songs.values())

    def list_albums(self):
        return list(self._albums.values())

    def list_artists(self):
        return list(self._artists.values())

    def get_song(self, identifier):
        return self._songs.get(identifier)

    def get_album(self, identifier):
        return self._albums.get(identifier)

    def get_artist(self, identifier):
        return self._artists.get(identifier)

    @log_exectime
    def scan(self, config, paths, depth, exts):
        """scan media files in all paths
        """
        media_files = []
        logger.info('start scanning...')
        for directory in paths:
            logger.debug('正在扫描目录(%s)...', directory)
            media_files.extend(scan_directory(directory, exts, depth))
        logger.info(f'scanning finished, {len(media_files)} files in total')

        for fpath in media_files:
            add_song(fpath, self._songs, self._artists, self._albums,
                     config.CORE_LANGUAGE,
                     config.IDENTIFIER_SPLITER,
                     config.EXPAND_ARTIST_SONGS)
        logger.info('录入本地音乐库完毕')

    def after_scan(self):
        """
        歌曲扫描完成后，对信息进行一些加工，比如
        1. 给专辑歌曲排序
        2. 给专辑和歌手加封面
        """
        def sort_album_func(album):
            if album.songs:
                return (album.songs[0].date is not None, album.songs[0].date)
            return (False, '0')

        for album in self._albums.values():
            try:
                album.songs.sort(key=lambda x: (int(x.disc.split('/')[0]),
                                                int(x.track.split('/')[0])))
                if album.name != 'Unknown':
                    cover_data, _ = read_audio_cover(album.songs[0].url)
                    if cover_data:
                        cover = Media(reverse(album.songs[0], '/cover/data'),
                                      type_=MediaType.image)
                    else:
                        cover = None
                    album.cover = cover
            except:  # noqa
                logger.exception('Sort album songs failed.')

        for artist in self._artists.values():
            if artist.albums:
                artist.albums.sort(key=sort_album_func, reverse=True)
                artist.cover = artist.albums[0].cover
            if artist.contributed_albums:
                artist.contributed_albums.sort(key=sort_album_func, reverse=True)
            if artist.songs:
                # sort artist songs
                artist.songs.sort(key=lambda x: x.title)
                # use song cover as artist cover
                # https://github.com/feeluown/feeluown-local/pull/3/files#r362126996
                songs_with_unknown_album = [song for song in artist.songs
                                            if song.album_name == 'Unknown']
                for song in sorted(songs_with_unknown_album,
                                   key=lambda x: (x.date is not None, x.date),
                                   reverse=True):
                    if read_audio_cover(song.url)[0]:
                        artist.cover = Media(reverse(song, '/cover/data'),
                                             type_=MediaType.image)
                        break


class LocalProvider(AbstractProvider, ProviderV2):
    class meta:
        identifier = SOURCE
        name = '本地音乐'
        flags = {
            ModelType.song: (PF.lyric),
        }

    def __init__(self):
        super().__init__()

        self._app = None
        self.library = Library()

    def initialize(self, app):
        self._app = app

    def scan(self, config, paths, depth=3):
        exts = config.MUSIC_FORMATS
        self.library.scan(config, paths, depth, exts)
        self.library.after_scan()

    @property
    def identifier(self):
        return SOURCE

    @property
    def name(self):
        return '本地音乐'

    @property
    def songs(self):
        return self.library.list_songs()

    @property
    def albums(self):
        return self.library.list_albums()

    @property
    def artists(self):
        return self.library.list_artists()

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
        # 歌词获取报错的 workaround
        if self._app is None:
            return None
        provider = self._app.library.get('qqmusic')
        if provider is None:
            return None
        result = provider.search(f'{song.title} {song.artists_name}', type_=SearchType.so)
        songs = result.songs
        if len(songs) < 1:
            return None
        return provider.song_get_lyric(songs[0]) or songs[0].lyric


provider = LocalProvider()


from .db import add_song  # noqa
from .models import LSearchModel  # noqa
