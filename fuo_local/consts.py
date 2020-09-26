import os
from feeluown.consts import DATA_DIR

MUSIC_FOLDERS = [os.path.expanduser('~') + '/Music']
# 由使用者确定需要过滤的文件类型
FORMATS = ['mp3', 'ogg', 'wma', 'm4a', 'm4v', 'flac']

# 由使用者确定显示和搜索需要用的主语言
CORE_LANGUAGE = 'cn'  # auto/cn/tc

ENABLE_WATCHER = True

ENABLE_DATABASE = True
DATABASE_FILE = os.path.join(DATA_DIR, 'database.json')

