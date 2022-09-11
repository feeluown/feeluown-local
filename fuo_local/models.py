import logging

from feeluown.models import (
    BaseModel,
    SongModel,
    AlbumModel,
    ArtistModel,
    SearchModel,
)
from feeluown.utils.reader import wrap

from .utils import read_audio_cover
from .provider import provider

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
        return cls.meta.provider.db.get_song(identifier)

    @classmethod
    def list(cls, identifier_list):
        return map(cls.meta.provider.db._songs.get, identifier_list)

    def resolve__cover_data(self, **kwargs):
        return read_audio_cover(self.url)[0]


class LAlbumModel(AlbumModel, LBaseModel):

    @classmethod
    def get(cls, identifier):
        return cls.meta.provider.db.get_album(identifier)


class LArtistModel(ArtistModel, LBaseModel):

    class Meta:
        fields = ('contributed_albums', )
        allow_create_albums_g = True

    @classmethod
    def get(cls, identifier):
        return cls.meta.provider.db.get_artist(identifier)

    def create_albums_g(self):
        return wrap(self.albums)

    def create_contributed_albums_g(self):
        return wrap(self.contributed_albums)


class LSearchModel(SearchModel, LBaseModel):
    pass
