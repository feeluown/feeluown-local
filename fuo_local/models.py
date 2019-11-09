import logging

from fuocore.models import (
    BaseModel,
    SongModel,
    AlbumModel,
    ArtistModel,
    SearchModel,
)
from fuocore.reader import RandomSequentialReader

from .provider import provider
from .utils import read_audio_cover

logger = logging.getLogger(__name__)


class LBaseModel(BaseModel):

    class Meta:
        allow_get = True
        provider = provider


class LSongModel(SongModel, LBaseModel):

    class Meta:
        fields = ('disc', 'genre', 'date', 'track', 'cover', 'desc')
        fields_no_get = ('lyric', )
        paths = [
            '/cover/data',
        ]

    @classmethod
    def get(cls, identifier):
        return cls.meta.provider.library.get_song(identifier)

    @classmethod
    def list(cls, identifier_list):
        return map(cls.meta.provider.library._songs.get, identifier_list)

    def resolve__cover_data(self, **kwargs):
        return read_audio_cover(self.url)[0]


class LAlbumModel(AlbumModel, LBaseModel):

    @classmethod
    def get(cls, identifier):
        return cls.meta.provider.library.get_album(identifier)


class LArtistModel(ArtistModel, LBaseModel):

    class Meta:
        allow_create_albums_g = True

    @classmethod
    def get(cls, identifier):
        return cls.meta.provider.library.get_artist(identifier)

    def create_albums_g(self):
        count = len(self.albums)
        read_func = lambda start, end: self.albums[start:end]
        # we can change max_per_read later when we need
        return RandomSequentialReader(count,
                                      read_func=read_func,
                                      max_per_read=1000)


class LSearchModel(SearchModel, LBaseModel):
    pass
