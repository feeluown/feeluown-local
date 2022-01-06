import base64
import logging
import os
import re

from marshmallow.exceptions import ValidationError
from mutagen import MutagenError
from mutagen.mp3 import EasyMP3
from mutagen.easymp4 import EasyMP4
from mutagen.flac import FLAC
from mutagen.apev2 import APEv2

from feeluown.utils.utils import elfhash
from fuocore.models import AlbumType

from .lans_helpers import core_lans
from .provider import read_audio_cover, Media, reverse, MediaType

from .schemas import (
    EasyMP3MetadataSongSchema,
    FLACMetadataSongSchema,
    APEMetadataSongSchema,
)
from .models import (
    LSongModel,
    LAlbumModel,
    LArtistModel,
)

logger = logging.getLogger(__name__)


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


def add_song(fpath, g_songs, g_artists, g_albums, lans='auto', delimiter='', expand_artist_songs=False):
    """
    parse music file metadata with Easymp3 and return a song
    model.
    """
    try:
        if fpath.endswith('mp3') or fpath.endswith('ogg') or fpath.endswith('wma'):
            metadata = EasyMP3(fpath)
        elif fpath.endswith('m4a') or fpath.endswith('m4v') or fpath.endswith('mp4'):
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
        metadata_dict[key] = core_lans(metadata_dict[key][0], lans)
    if 'title' not in metadata_dict:
        title = os.path.split(fpath)[-1].split('.')[0]
        metadata_dict['title'] = core_lans(title, lans)
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
    # 加入分隔符'-'在一定概率上更能确保不发生哈希值重复
    song_id_str = delimiter.join([title, artists_name, album_name, str(int(duration))])
    song_id = gen_id(song_id_str)
    if song_id not in g_songs:
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
    album_id_str = delimiter.join([album_name, album_artist_name])
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
    if expand_artist_songs and song not in album_artist.songs:
        album_artist.songs.append(song)


class DB:
    """
    DB manages a fileset and their corresponding models

    the data structure in db file::

        {
          "files": [],
          "songs": []
        }
    """
    def __init__(self, fpath):
        """
        :param filepath: database file path
        """

        self._dirty = False  # whether changes are flushed
        self._fileset = set()  # media files

        self._songs = []
        self._artists = []
        self._albums = []

    def flush(self):
        """flush the changes into db file"""

    def list_models(self):
        """list all models in database"""
        pass

    def add(self, fpath):
        """add media file to database"""
        add_song(fpath, self._songs, self._artists, self._albums)

    def remove(self, fpath):
        """add media file to database"""
