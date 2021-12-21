# -*- coding: utf-8 -*-
import asyncio
import logging
from functools import partial

from fuocore import aio

from .patch import patch_mutagen
patch_mutagen()

from .provider import provider

__alias__ = '本地音乐'
__feeluown_version__ = '1.1.0'
__version__ = '0.1a0'
__desc__ = '本地音乐'

logger = logging.getLogger(__name__)


def init_config(config):
    config.deffield('MUSIC_FOLDERS', type_=list, default=None, desc='')
    config.deffield('MUSIC_FORMATS', type_=list, default=None, desc='')


def show_provider(req):
    from .ui import LibraryRenderer
    if hasattr(req, 'ctx'):
        app = req.ctx['app']
    else:
        app = req  # 兼容老版本
    app.pl_uimgr.clear()
    # app.playlists.add(provider.playlists)

    app.ui.left_panel.my_music_con.hide()
    app.ui.left_panel.playlists_con.hide()

    aio.create_task(app.ui.table_container.set_renderer(
        LibraryRenderer(provider.songs, provider.albums, provider.artists)))


def autoload(app):
    loop = asyncio.get_event_loop()
    future_scan = loop.run_in_executor(None, provider.scan,
                                       app.config.fuo_local,
                                       app.config.fuo_local.MUSIC_FOLDERS)
    app.library.register(provider)
    if app.mode & app.GuiMode:
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


def enable(app):
    logger.info('Register provider: %s', provider)
    app.initialized.connect(lambda app: autoload(app), weak=False, aioqueue=True)


def disable(app):
    logger.info('唔，不要禁用我')
