# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""
TODO: 这个模块中目前逻辑非常多，包括音乐目录扫描、音乐库的构建等小部分，
这些小部分理论都可以从中拆除。
"""

import base64
import logging
import os
import re

from fuzzywuzzy import process
from marshmallow.exceptions import ValidationError
from mutagen import MutagenError
from mutagen.mp3 import EasyMP3
from mutagen.easymp4 import EasyMP4
from mutagen.flac import FLAC
from mutagen.apev2 import APEv2
from fuocore.provider import AbstractProvider
from fuocore.utils import elfhash
from fuocore.utils import log_exectime
from fuocore.media import Media, MediaType
from fuocore.models import AlbumType
from fuocore.models import reverse

from .consts import FORMATS, ENABLE_WATCHER, ENABLE_DATABASE, DATABASE_FILE
from .multi_lans import core_lans
from .database import load_database, save_database
from .watcher import watcher
from .utils import read_audio_cover

logger = logging.getLogger(__name__)


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


def gen_id(s):
    return str(elfhash(base64.b64encode(bytes(s, 'utf-8'))))


def create_artist(identifier, name):
    return LArtistModel(identifier=identifier,
                        name=name,
                        songs=[],
                        albums=[],
                        contributed_albums=[],
                        desc='',
                        cover='',)


def create_album(identifier, name, cover):
    """create album model with album name
    """
    album = LAlbumModel(identifier=identifier,
                        name=name,
                        songs=[],
                        artists=[],
                        desc='',
                        cover=cover,)
    # guess album type by its name
    #
    # album name which contains following string are `Single`
    #   1. ' - Single'  6+3=9
    #   2. '(single)'   6+2=8
    #   3. '（single）'  6+2=8
    if 'single' in name[-9:].lower():
        album.type = AlbumType.single
    if 'ep' in name[-5:].lower():
        album.type = AlbumType.ep
    return album


def add_song(fpath, g_files, g_songs, g_artists, g_albums):
    """
    parse music file metadata with Easymp3 and return a song
    model.
    """
    try:
        if fpath.endswith('mp3') or fpath.endswith('ogg') or fpath.endswith('wma'):
            metadata = EasyMP3(fpath)
        elif fpath.endswith('m4a') or fpath.endswith('m4v'):
            metadata = EasyMP4(fpath)
        elif fpath.endswith('flac'):
            metadata = FLAC(fpath)
        elif fpath.endswith('ape'):
            metadata = APEv2(fpath)
        elif fpath.endswith('wav'):
            metadata = dict()
    except MutagenError as e:
        logger.warning(
            'Mutagen parse metadata failed, ignore.\n'
            'file: {}, exception: {}'.format(fpath, str(e)))
        return None

    metadata_dict = dict(metadata)
    for key in metadata.keys():
        metadata_dict[key] = core_lans(metadata_dict[key][0])
    if 'title' not in metadata_dict:
        title = os.path.split(fpath)[-1].split('.')[0]
        metadata_dict['title'] = title
    metadata_dict.update(dict(
        url=fpath,
        duration=metadata.info.length * 1000  # milesecond
    ))

    try:
        if fpath.endswith('flac'):
            data = FLACMetadataSongSchema().load(metadata_dict)
        elif fpath.endswith('ape'):
            data = APEMetadataSongSchema().load(metadata_dict)
        else:
            data = EasyMP3MetadataSongSchema().load(metadata_dict)
    except ValidationError:
        logger.exception('解析音乐文件({}) 元数据失败'.format(fpath))
        return

    # NOTE: use {title}-{artists_name}-{album_name} as song identifier
    title = data['title']
    album_name = data['album_name']
    artist_name_list = [
        name.strip()
        for name in re.split(r'[,&]', data['artists_name'])]
    artists_name = ','.join(artist_name_list)
    duration = data['duration']
    album_artist_name = data['album_artist_name']

    # 生成 song model
    # 用来生成 id 的字符串应该尽量减少无用信息，这样或许能减少 id 冲突概率
    # 加入分隔符"-"在一定概率上更能确保不发生哈希值重复
    song_id_str = '-'.join([title, artists_name, album_name, str(int(duration))])
    song_id = gen_id(song_id_str)
    if song_id not in g_songs:
        g_files[fpath] = song_id
        # 剩下 album, lyric 三个字段没有初始化
        song = LSongModel(identifier=song_id,
                          artists=[],
                          title=title,
                          url=fpath,
                          duration=duration,
                          comments=[],
                          # 下面这些字段不向外暴露
                          genre=data['genre'],
                          cover=data['cover'],
                          date=data['date'],
                          desc=data['desc'],
                          disc=data['disc'],
                          track=data['track'])
        g_songs[song_id] = song
    else:
        song = g_songs[song_id]
        # 继续监视哈希函数性能
        logger.warning('Duplicate song: %s %s', song.url, fpath)
        return

    # 生成 album artist model
    album_artist_id = gen_id(album_artist_name)
    if album_artist_id not in g_artists:
        album_artist = create_artist(album_artist_id, album_artist_name)
        g_artists[album_artist_id] = album_artist
    else:
        album_artist = g_artists[album_artist_id]

    # 生成 album model
    album_id_str = '-'.join([album_name, album_artist_name])
    album_id = gen_id(album_id_str)
    # cover_data, cover_fmt = read_audio_cover(fpath)
    # if cover_data is None:
    #     cover = None
    # else:
    #     cover = Media(reverse(song, '/cover/data'), type_=MediaType.image)
    if album_id not in g_albums:
        album = create_album(album_id, album_name, None)
        g_albums[album_id] = album
    else:
        album = g_albums[album_id]

    # 处理专辑的歌手信息和歌曲信息，专辑歌手的专辑列表信息
    if album not in album_artist.albums:
        album_artist.albums.append(album)
    if album_artist not in album.artists:
        album.artists.append(album_artist)
    if song not in album.songs:
        album.songs.append(song)

    # 处理歌曲的歌手和专辑信息，以及歌手的歌曲列表和参与作品
    song.album = album
    for artist_name in artist_name_list:
        artist_id = gen_id(artist_name)
        if artist_id in g_artists:
            artist = g_artists[artist_id]
        else:
            artist = create_artist(identifier=artist_id, name=artist_name)
            g_artists[artist_id] = artist
        if artist not in song.artists:
            song.artists.append(artist)
        if song not in artist.songs:
            artist.songs.append(song)

        # 处理歌曲歌手的参与作品信息(不与前面的重复)
        if album not in artist.albums and album not in artist.contributed_albums:
            artist.contributed_albums.append(album)

    # 处理专辑歌手的歌曲信息: 有些作词人出合辑很少出现在歌曲歌手里(可选)
    # if song not in album_artist.songs:
    #     album_artist.songs.append(song)


class Library:
    DEFAULT_MUSIC_FOLDER = os.path.expanduser('~') + '/Music'

    def __init__(self):
        self._songs = {}
        self._albums = {}
        self._artists = {}
        self._files = {}

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
    def scan(self, paths=None, depth=2):
        """scan media files in all paths
        """
        song_exts = FORMATS
        exts = song_exts
        paths = paths or [Library.DEFAULT_MUSIC_FOLDER]
        depth = depth if depth <= 3 else 3
        media_files = []
        for directory in paths:
            logger.debug('正在扫描目录(%s)...', directory)
            media_files.extend(scan_directory(directory, exts, depth))
        logger.info('共扫描到 %d 个音乐文件，准备将其录入本地音乐库', len(media_files))

        if ENABLE_DATABASE and os.path.exists(DATABASE_FILE):
            load_database(media_files, self._files, self._songs, self._artists, self._albums)
        else:
            for fpath in media_files:
                add_song(fpath, self._files, self._songs, self._artists, self._albums)
            save_database(self._files, self._songs, self._artists, self._albums)
        logger.info('录入本地音乐库完毕')

    @log_exectime
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
                album.songs.sort(key=lambda x: (int(x.disc.split('/')[0]), int(x.track.split('/')[0])))
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

    def start_watcher(self, paths):
        from fuocore import aio
        aio.create_task(
            watcher(paths or [Library.DEFAULT_MUSIC_FOLDER], self._files, self._songs, self._artists, self._albums))


class LocalProvider(AbstractProvider):

    def __init__(self):
        super().__init__()

        self.library = Library()

    def scan(self, paths=None, depth=3):
        self.library.scan(paths, depth)
        self.library.after_scan()
        if ENABLE_WATCHER:
            self.library.start_watcher(paths)

    @property
    def identifier(self):
        return 'local'

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


provider = LocalProvider()

from .schemas import EasyMP3MetadataSongSchema, FLACMetadataSongSchema, APEMetadataSongSchema
from .models import (
    LSearchModel,
    LSongModel,
    LAlbumModel,
    LArtistModel,
)
