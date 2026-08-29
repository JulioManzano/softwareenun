import django_filters
from .models import Channel, FavoriteChannel, FavoriteMovie, Movie

class ChannelFilter(django_filters.FilterSet):
    user_id = django_filters.NumberFilter(method='filter_user')

    country = django_filters.CharFilter(lookup_expr='iexact')
    category = django_filters.CharFilter(lookup_expr='iexact')
    is_premium = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    source = django_filters.CharFilter(lookup_expr='iexact')
    ordering = django_filters.CharFilter(method='filter_ordering')

    class Meta:
        model = Channel
        fields = [
            'id',
            'name',
            'country',
            'category',
            'is_premium',
            'is_active',
            'use_hls',
            'source',
            'ordering',
            'user_id',
        ]
        
    def filter_user(self, queryset, name, value):
        if not value:
            return queryset

        if not value:
            return queryset

        favorites = FavoriteChannel.objects.filter(
            user_id=value
        ).values_list('channel_id', flat=True)

        return queryset.filter(id__in=favorites)    
   

    def filter_ordering(self, queryset, name, value):
        allowed_fields = [
            'name', '-name',
            'rating', '-rating',
            'created_at', '-created_at',
        ]

        if value in allowed_fields:
            return queryset.order_by(value)

        return queryset.order_by('name')
    
class MovieFilter(django_filters.FilterSet):
    user_id = django_filters.NumberFilter(method='filter_user')

    category = django_filters.NumberFilter(field_name='categories__id')
    year = django_filters.NumberFilter()
    is_active = django_filters.BooleanFilter()
    ordering = django_filters.CharFilter(method='filter_ordering')

    class Meta:
        model = Movie
        fields = [
            'id',
            'title',
            'year',
            'is_active',
            'category',
            'ordering',
            'user_id',
        ]
        
    def filter_user(self, queryset, name, value):
        if not value:
            return queryset

        if not value:
            return queryset

        favorites = FavoriteMovie.objects.filter(
            user_id=value
        ).values_list('movie_id', flat=True)

        return queryset.filter(id__in=favorites)
    
   

    def filter_ordering(self, queryset, name, value):
        allowed_fields = [
            'title', '-title',
            'year', '-year',
            'created_at', '-created_at',
        ]

        if value in allowed_fields:
            return queryset.order_by(value)

        return queryset.order_by('-created_at')

    def filter_ordering(self, queryset, name, value):
        allowed_fields = [
            'title', '-title',
            'year', '-year',
            'created_at', '-created_at',
        ]

        if value in allowed_fields:
            return queryset.order_by(value)

        return queryset.order_by('-created_at')