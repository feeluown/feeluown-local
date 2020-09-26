import logging
logger = logging.getLogger(__name__)


def delete_song(fpath, g_files, g_songs, g_artists, g_albums):
    song = g_songs.get(g_files.get(fpath))

    album = song.album
    if album:
        album.songs.remove(song)
        if not album.songs:
            g_albums.pop(album.identifier)
            for artist in album.artists:
                artist.albums.remove(album)
                if not artist.albums and not artist.contributed_albums and not artist.songs:
                    g_artists.pop(artist.identifier)
            for artist in song.artists:
                if artist not in album.artists:
                    artist.contributed_albums.remove(album)
                    if not artist.albums and not artist.contributed_albums and not artist.songs:
                        g_artists.pop(artist.identifier)
        else:
            for artist in song.artists:
                if artist not in album.artists:
                    need_to_remove = True
                    for _song in album.songs:
                        if artist in _song.artists:
                            need_to_remove = False
                    if need_to_remove:
                        artist.contributed_albums.remove(album)
                        if not artist.albums and not artist.contributed_albums and not artist.songs:
                            g_artists.pop(artist.identifier)

    for artist in song.artists:
        artist.songs.remove(song)
        if not artist.albums and not artist.contributed_albums and not artist.songs:
            g_artists.pop(artist.identifier)

    g_songs.pop(song.identifier)


def delete_song_and_after_delete(fpath, g_files, g_songs, g_artists, g_albums):
    from .provider import read_audio_cover, Media, reverse, MediaType

    song = g_songs.get(g_files.get(fpath))

    album = song.album
    if album:
        album.songs.remove(song)
        if not album.songs:
            g_albums.pop(album.identifier)
            for artist in album.artists:
                artist.albums.remove(album)
                if not artist.albums and not artist.contributed_albums and not artist.songs:
                    g_artists.pop(artist.identifier)
                else:
                    if artist.albums:
                        artist.cover = artist.albums[0].cover
            for artist in song.artists:
                if artist not in album.artists:
                    artist.contributed_albums.remove(album)
                    if not artist.albums and not artist.contributed_albums and not artist.songs:
                        g_artists.pop(artist.identifier)
        else:
            for artist in song.artists:
                if artist not in album.artists:
                    need_to_remove = True
                    for _song in album.songs:
                        if artist in _song.artists:
                            need_to_remove = False
                    if need_to_remove:
                        artist.contributed_albums.remove(album)
                        if not artist.albums and not artist.contributed_albums and not artist.songs:
                            g_artists.pop(artist.identifier)
            if album.name != 'Unknown':
                cover_data, _ = read_audio_cover(album.songs[0].url)
                if cover_data:
                    cover = Media(reverse(album.songs[0], '/cover/data'),
                                  type_=MediaType.image)
                else:
                    cover = None
                album.cover = cover

    for artist in song.artists:
        artist.songs.remove(song)
        if not artist.albums and not artist.contributed_albums and not artist.songs:
            g_artists.pop(artist.identifier)
        else:
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

    g_songs.pop(song.identifier)


def after_add(song):
    from .provider import read_audio_cover, Media, reverse, MediaType

    def sort_album_func(album):
        if album.songs:
            return (album.songs[0].date is not None, album.songs[0].date)
        return (False, '0')

    album = song.album
    if album:
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
        for artist in album.artists:
            artist.albums.sort(key=sort_album_func, reverse=True)
            artist.cover = artist.albums[0].cover
        for artist in song.artists:
            if artist not in album.artists:
                artist.contributed_albums.sort(key=sort_album_func, reverse=True)
    for artist in song.artists:
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
