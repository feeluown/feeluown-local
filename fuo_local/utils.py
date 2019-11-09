from mutagen.id3 import ID3
from mutagen.mp4 import MP4, AtomDataType


def read_audio_cover(fpath):
    """read audio cover binary data and format"""

    if fpath.endswith('mp3') or fpath.endswith('ogg') or fpath.endswith('wma'):
        id3 = ID3(fpath)
        apic = id3.get('APIC:')
        if apic is not None:
            if apic.mime in ('image/jpg', 'img/jpeg'):
                fmt = 'jpg'
            else:
                fmt = 'png'
            return apic.data, fmt

    elif fpath.endswith('m4a'):
        mp4 = MP4(fpath)
        tags = mp4.tags
        if tags is not None:
            covers = tags.get('covr')
            if covers:
                cover = covers[0]
                if cover.imageformat == AtomDataType.JPEG:
                    fmt = 'jpg'
                else:
                    fmt = 'png'
                return cover.data, fmt

    return None, None
