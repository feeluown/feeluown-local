import logging

from fuocore.models import (
    BaseModel,
    SongModel,
    AlbumModel,
    ArtistModel,
    SearchModel,
)

from .provider import provider

logger = logging.getLogger(__name__)


class LBaseModel(BaseModel):
    _detail_fields = ()

    class Meta:
        allow_get = True
        provider = provider


class LSongModel(SongModel, LBaseModel):
    class Meta:
        fields = ('disc', 'genre', 'date', 'track', 'cover', 'desc')
        fields_no_get = ('lyric', )

    @classmethod
    def get(cls, identifier):
        return cls.meta.provider.library.get_song(identifier)

    @classmethod
    def list(cls, identifier_list):
        return map(cls.meta.provider.library._songs.get, identifier_list)


class LAlbumModel(AlbumModel, LBaseModel):
    _detail_fields = ('songs', )

    @classmethod
    def get(cls, identifier):
        return cls.meta.provider.library.get_album(identifier)


class LArtistModel(ArtistModel, LBaseModel):
    _detail_fields = ('songs', )

    class Meta:
        fields = ('albums2', 'albums3')
        allow_create_albums_g = True

    @classmethod
    def get(cls, identifier):
        return cls.meta.provider.library.get_artist(identifier)

    # 可能存在的问题: 如果专辑过多时，是否能一次性选择全部？毕竟这是本地库
    def create_albums_g(self):
        for album in self.albums:
            yield album

    def create_albums2_g(self):
        for album in self.albums2:
            yield album

    def create_albums3_g(self):
        for album in self.albums3:
            yield album


class LSearchModel(SearchModel, LBaseModel):
    pass
