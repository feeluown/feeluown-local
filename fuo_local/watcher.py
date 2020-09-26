from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

import logging
logger = logging.getLogger(__name__)

from .helpers import delete_song_and_after_delete, after_add


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, files=[], songs=[], artists=[], albums=[]):
        FileSystemEventHandler.__init__(self)
        self.files = files
        self.songs = songs
        self.artists = artists
        self.albums = albums

    def on_moved(self, event):
        if not event.is_directory:
            fpath = event.src_path
            if fpath.endswith('mp3') or fpath.endswith('ogg') or fpath.endswith('wma') \
                    or fpath.endswith('m4a') or fpath.endswith('m4v'):
                logger.info('file moved from {0} to {1}'.format(event.src_path, event.dest_path))

                song = self.songs[self.files.pop(fpath)]
                song.url = event.dest_path
                self.files[song.url] = song.identifier

    def on_created(self, event):
        if not event.is_directory:
            fpath = event.src_path
            if fpath.endswith('mp3') or fpath.endswith('ogg') or fpath.endswith('wma') \
                    or fpath.endswith('m4a') or fpath.endswith('m4v'):
                logger.info('file created:{0}'.format(event.src_path))

                from .provider import add_song
                add_song(fpath, self.files, self.songs, self.artists, self.albums)
                after_add(self.songs.get(self.files.get(fpath)))

    def on_deleted(self, event):
        if not event.is_directory:
            fpath = event.src_path
            if fpath.endswith('mp3') or fpath.endswith('ogg') or fpath.endswith('wma') \
                    or fpath.endswith('m4a') or fpath.endswith('m4v'):
                logger.info('file deleted:{0}'.format(fpath))

                delete_song_and_after_delete(fpath, self.files, self.songs, self.artists, self.albums)

    def on_modified(self, event):
        if not event.is_directory:
            fpath = event.src_path
            if fpath.endswith('mp3') or fpath.endswith('ogg') or fpath.endswith('wma') \
                    or fpath.endswith('m4a') or fpath.endswith('m4v'):
                logger.info('file deleted:{0}'.format(fpath))

                delete_song_and_after_delete(fpath, self.files, self.songs, self.artists, self.albums)
                from .provider import add_song
                add_song(fpath, self.files, self.songs, self.artists, self.albums)
                after_add(self.songs.get(self.files.get(fpath)))


# FIXME: watcher目前还没有办法正常退出
def watcher(paths, files, songs, albums, artists):
    observer = Observer()
    for path in paths:
        event_handler = FileEventHandler(files, songs, albums, artists)
        # FIXME: use fixed depth with 'depth'
        observer.schedule(event_handler, path, True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
