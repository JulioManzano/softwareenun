from graphene_django import DjangoObjectType
import graphene
from django.db.models import Case, When, BooleanField, Value
from channel.models import Channel, FavoriteChannel, FavoriteMovie, Movie
from graphene_django_extras import DjangoListObjectType
from graphene_django_extras.paginations import LimitOffsetGraphqlPagination

class ChannelListType(DjangoListObjectType):
    class Meta:
        model = Channel
        pagination = LimitOffsetGraphqlPagination(default_limit=25)
        

class ChannelType(DjangoObjectType):
    id = graphene.Int()
    is_favorite = graphene.Boolean()

    class Meta:
        model = Channel
        fields = "__all__"

    def resolve_id(self, info):
        return self.pk

    def resolve_is_favorite(self, info):
        return getattr(self, "is_favorite", False)

    @classmethod
    def get_queryset(cls, queryset, info):
        request = info.context
        user_id = request.GET.get("userId")

        if user_id:
            favorites = FavoriteChannel.objects.filter(
                user_id=user_id

            ).values_list("channel_id", flat=True)

            queryset = queryset.annotate(
                is_favorite=Case(
                    When(id__in=favorites, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                )
            )

        return queryset


class MovieListType(DjangoListObjectType):
    class Meta:
        model = Movie
        pagination = LimitOffsetGraphqlPagination(default_limit=25)

class MovieType(DjangoObjectType):
    id = graphene.Int()
    is_favorite = graphene.Boolean()

    class Meta:
        model = Movie
        fields = "__all__"

    def resolve_id(self, info):
        return self.pk

    def resolve_is_favorite(self, info):
        return getattr(self, "is_favorite", False)

    @classmethod
    def get_queryset(cls, queryset, info):
        request = info.context
        user_id = (
            request.GET.get("user_id")
            or request.GET.get("user_id")
        )

        if user_id:
            favorites = FavoriteMovie.objects.filter(
                user_id=user_id
            ).values_list("movie_id", flat=True)

            queryset = queryset.annotate(
                is_favorite=Case(
                    When(id__in=favorites, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                )
            )

        return queryset