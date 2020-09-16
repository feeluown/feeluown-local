# -*- coding: utf-8 -*-

import asyncio
import logging
from functools import partial
from .patch import patch_mutagen
patch_mutagen()
from .provider import provider

__alias__ = '本地音乐'
__feeluown_version__ = '1.1.0'
__version__ = '0.1a0'
__desc__ = '本地音乐'

logger = logging.getLogger(__name__)


def show_provider(req):
    if hasattr(req, 'ctx'):
        app = req.ctx['app']
    else:
        app = req  # 兼容老版本
    app.pl_uimgr.clear()
    # app.playlists.add(provider.playlists)

    app.ui.left_panel.my_music_con.hide()
    app.ui.left_panel.playlists_con.hide()

    from contextlib import suppress
    from requests.exceptions import RequestException
    from fuocore import aio
    from fuocore.excs import ProviderIOError
    from feeluown.helpers import async_run
    from feeluown.containers.table import Renderer

    class LibraryRenderer(Renderer):
        def __init__(self, songs, albums, artists):
            self.songs = songs
            self.albums = albums
            self.artists = artists

        async def render(self):
            self.meta_widget.show()
            self.tabbar.show()
            self.tabbar.library_mode()

            # fetch and render songs
            songs = await async_run(lambda: self.songs)
            self.show_songs(songs_g=None, songs=songs, show_count=True)
            self.tabbar.show_songs_needed.connect(
                lambda: self.show_songs(songs_g=None,
                                        songs=songs,
                                        show_count=True))

            # fetch and render albums
            self.tabbar.show_albums_needed.connect(lambda: aio.create_task(self._show_albums()))

            # fetch and render artists
            self.tabbar.show_artists_needed.connect(lambda: aio.create_task(self._show_artists()))

        async def _show_albums(self):
            with suppress(ProviderIOError, RequestException):
                albums = await async_run(lambda: self.albums)
                self.toolbar.filter_albums_needed.connect(
                    lambda types: self.albums_table.model().filter_by_types(types))
                self.tabbar.show_albums_needed.connect(
                    lambda: self.show_albums(albums))

        async def _show_artists(self):
            with suppress(ProviderIOError, RequestException):
                artists = await async_run(lambda: self.artists)
                self.tabbar.show_artists_needed.connect(
                    lambda: self.show_artists(artists))

    aio.create_task(app.ui.table_container.set_renderer(
        LibraryRenderer(provider.songs, provider.albums, provider.artists)))


def enable(app):
    from feeluown.app import App

    logger.info('Register provider: %s', provider)
    loop = asyncio.get_event_loop()
    future_scan = loop.run_in_executor(None, provider.scan)
    app.library.register(provider)
    if app.mode & App.GuiMode:
        app.browser.route('/local')(show_provider)
        pm = app.pvd_uimgr.create_item(
            name=provider.identifier,
            text='本地音乐',
            symbol='♪ ',
            desc='点击显示所有本地音乐',
        )
        pm.clicked.connect(partial(app.browser.goto, uri='/local'), weak=False)
        app.pvd_uimgr.add_item(pm)
        future_scan.add_done_callback(lambda _: app.coll_uimgr.refresh())
        future_scan.add_done_callback(lambda _: app.show_msg('本地音乐扫描完毕'))


def disable(app):
    logger.info('唔，不要禁用我')
