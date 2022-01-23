# feeluown 本地音乐插件

## 安装

```sh
pip3 install fuo-local
```

## 配置

```python
# In ~/.fuorc

import os
def load_plugin_rcfiles(plugin):
    if plugin.name == 'fuo_local':
        config.fuo_local.MUSIC_FOLDERS = [os.path.expanduser('~') + '/Music']
        config.fuo_local.MUSIC_FORMATS = ['mp3', 'ogg', 'wma', 'm4a', 'm4v', 'mp4', 'flac']

when('app.plugin_mgr.about_to_enable', load_plugin_rcfiles, use_symbol=True, aioqueue=False)
```



## TODO

此插件目前功能非常基础，有很多可以改进的地方，从功能到性能。
下面列了一些可以改进的方面：

- [ ] 支持自定义歌曲目录
- [ ] 增量扫描？
- [ ] 支持更多格式的音乐
- ...

## changelog

### 0.3 (2021-01-23)
- 适配 feeluown>=3.8.1
- 支持更多音乐格式

### 0.2 (2019-11-26)
- 适配 feeluown>=3.2a0
- 使用 3.x 的 marshmallow

### 0.1.3
- 修复：歌曲为空时，search 报错
- 适配 feeluown 3.1

### 0.1.2 (2019-05-05)
- 修复 windows 下路径解析错误
- 更好的解析 id3 信息编码为 GBK 的音乐文件

### 0.1.1 (2019-03-23)
- 适配 feeluown 3.0a5+

### 0.1 (2019-03-18)
- 支持扫描 `~/Music` 目录的本地音乐
