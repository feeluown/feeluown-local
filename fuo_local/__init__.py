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
    app.ui.songs_table_container.show_songs(provider.songs)


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
        future_scan.add_done_callback(lambda _: app.show_msg('本地音乐扫描完毕'))


def disable(app):
    logger.info('唔，不要禁用我')
