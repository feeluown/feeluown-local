import os
import time

from .consts import DATABASE_FILE
# from .provider import add_song
# from .helpers import delete_song
# from fuocore.serializers import serialize
# from .models import LSongModel, LArtistModel, LAlbumModel

def _get_modified_time(media_files):
    result = dict()

    for fpath in media_files:
        filemt = os.stat(fpath).st_mtime
        local_time = time.localtime(filemt)
        data_head = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
        data_secs = (filemt - int(filemt)) * 1000
        time_stamp = "%s.%03d" % (data_head, data_secs)

        result[fpath] = time_stamp

    return result


def _generate_database_files(files):
    result = []

    for fpath in files.keys():
        filemt = os.stat(fpath).st_mtime
        local_time = time.localtime(filemt)
        data_head = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
        data_secs = (filemt - int(filemt)) * 1000
        time_stamp = "%s.%03d" % (data_head, data_secs)

        result.append({'uri': fpath,
                       'identifier': files.get(fpath),
                       'modified_time': time_stamp})

    return result


def _generate_database_songs(songs):
    result = []

    for identifier in songs.keys():
        song = songs.get(identifier)
        song_dict = {
            'identifier': song.identifier,
            'title': song.title,
            'url': song.url,
            'artists': [{'identifier': artist.identifier} for artist in song.artists],
            'album': {'identifier': song.album.identifier} if song.album else None,
            'disc': song.disc,
            'track': song.track,
            'duration': song.duration,
            'date': song.date,
            'genre': song.genre
        }

        result.append(song_dict)

    return result


def _generate_database_artists(artists):
    result = []

    for identifier in artists.keys():
        artist = artists.get(identifier)
        artist_dict = {
            'identifier': artist.identifier,
            'name': artist.name,
            'songs': [{'identifier': song.identifier} for song in artist.songs],
            'albums': [{'identifier': album.identifier} for album in artist.albums],
            'contributed_albums': [{'identifier': album.identifier} for album in artist.contributed_albums]
        }

        result.append(artist_dict)

    return result


def _generate_database_albums(albums):
    result = []

    for identifier in albums.keys():
        album = albums.get(identifier)
        album_dict = {
            'identifier': album.identifier,
            'name': album.name,
            'artists': [{'identifier': artist.identifier} for artist in album.artists],
            'songs': [{'identifier': song.identifier} for song in album.songs]
        }

        result.append(album_dict)

    return result


def _json_parser(files, songs, artists, albums):
    from .models import LSongModel, LArtistModel, LAlbumModel

    import json
    with open(DATABASE_FILE, 'r') as f:
        result = json.load(f)

    time_dict = dict()
    for file in result['files']:
        files[file['uri']] = file['identifier']
        time_dict[file['uri']] = file['modified_time']

    for song in result['songs']:
        song_model = LSongModel(identifier=song['identifier'],
                           artists=[LArtistModel(identifier=artist['identifier']) for artist in song['artists']],
                           album=LAlbumModel(identifier=song['album']['identifier']) if song['album'] else None,
                           title=song['title'],
                           url=song['url'],
                           duration=song['duration'],
                           genre=song['genre'],
                           date=song['date'],
                           disc=song['disc'],
                           track=song['track'])
        songs[song['identifier']] = song_model

    for artist in result['artists']:
        artist_model = LArtistModel(identifier=artist['identifier'],
                           name=artist['name'],
                           songs=[LSongModel(identifier=song['identifier']) for song in artist['songs']],
                           albums=[LAlbumModel(identifier=album['identifier']) for album in artist['albums']],
                           contributed_albums=[LAlbumModel(identifier=album['identifier']) for album in artist['contributed_albums']])
        artists[artist['identifier']] = artist_model

    for album in result['albums']:
        album_model = LAlbumModel(identifier=album['identifier'],
                           name=album['name'],
                           artists=[LArtistModel(identifier=artist['identifier']) for artist in album['artists']],
                           songs=[LSongModel(identifier=song['identifier']) for song in album['songs']])
        albums[album['identifier']] = album_model

    return time_dict


def update_database(time_dict, newest_time_dict, files, songs, artists, albums):
    need_to_modified = [time_dict[uri]
                        for uri in set(time_dict.keys()).intersection(set(newest_time_dict.keys()))
                        if time_dict[uri] != newest_time_dict[uri]]

    need_to_delete = list(set(time_dict.keys()).difference(set(newest_time_dict.keys())))
    need_to_add = list(set(newest_time_dict.keys()).difference(set(time_dict.keys())))

    from .provider import add_song
    from .helpers import delete_song
    for fpath in need_to_delete + need_to_modified:
        delete_song(fpath, files, songs, artists, albums)
    for fpath in need_to_add + need_to_modified:
        add_song(fpath, files, songs, artists, albums)

    # save_database(files, songs, artists, albums)



def load_database(media_files, files, songs, artists, albums):
    # 读取DATABASE_PATH的数据, 包括files的修改时间
    time_dict = _json_parser(files, songs, artists, albums)
    # 确定media_files的修改时间
    newest_time_dict = _get_modified_time(media_files)
    # 对比确定需要更新的数据, 并依次进行删除、增加的操作(无移动)，然后更新songs/artists/albums
    update_database(time_dict, newest_time_dict, files, songs, artists, albums)


def save_database(files, songs, artists, albums):
    # 保存 文件及最后修改时间, 歌曲数据, 专辑数据, 艺术家数据
    result = {
        'files': _generate_database_files(files),
        'songs': _generate_database_songs(songs),
        'artists': _generate_database_artists(artists),
        'albums': _generate_database_albums(albums)
    }
    # for song in songs.values():
    #     result['songs'].append(serialize('json', song, indent=4, as_line=False, brief=False))
    # for artist in artists.values():
    #     result['artists'].append(serialize('json', artist, indent=4, as_line=False, brief=False))
    # for album in albums.values():
    #     result['albums'].append(serialize('json', album, indent=4, as_line=False, brief=False))

    import json
    with open(DATABASE_PATH, 'w') as f:
        json.dump(result, f)
