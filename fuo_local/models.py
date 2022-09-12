import logging

from feeluown.models import SearchModel
from feeluown.utils.reader import wrap
from .provider import provider

logger = logging.getLogger(__name__)



class LSearchModel(SearchModel):
    class Meta:
        provider = provider
