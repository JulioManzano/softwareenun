import graphene
from channel.models import Channel
from .types import ChannelListType, ChannelType, MovieListType
from .filters import ChannelFilter, MovieFilter
from graphene_django_extras import  DjangoListObjectField

class Query(graphene.ObjectType):
    channels = DjangoListObjectField(
        ChannelListType,
        filterset_class=ChannelFilter,
        
    ) 
    channel = graphene.Field(
        ChannelType,
        id=graphene.ID(required=True)
    )

    def resolve_channel(self, info, id):
        return Channel.objects.filter(id=id).first()
    
    movies = DjangoListObjectField(
        MovieListType,
        filterset_class=MovieFilter,
    )