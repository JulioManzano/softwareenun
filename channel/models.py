from django.db import models
from core.models import User


class Channel(models.Model):
    name = models.CharField(max_length=255, verbose_name='Nombre')
    logo = models.URLField(max_length=1000, blank=True)
    url = models.URLField(verbose_name='URL de streaming',max_length=1000)

    use_hls = models.BooleanField(default=False, verbose_name='Usa HLS')
    link_direct = models.BooleanField(default=False, verbose_name='Link directo')

    language = models.CharField(max_length=10, default='es', verbose_name='Idioma')
    country = models.CharField(max_length=10, default='AR', verbose_name='País')
    category = models.CharField(max_length=255, default='General', verbose_name='Categoría')

    is_premium = models.BooleanField(default=False, verbose_name='Es Premium')
    description = models.TextField(blank=True, default='', verbose_name='Descripción')

    rating = models.FloatField(null=True, blank=True, verbose_name='Rating')
    order = models.IntegerField(null=True, blank=True, verbose_name='Orden')

    headers = models.JSONField(default=dict, blank=True, verbose_name='Headers')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado')
    
    is_active = models.BooleanField(default=True)
    source = models.CharField(max_length=255, default='IPTV/ORG', verbose_name='Fuente')
    def __str__(self):
        return self.name
    
class CategoryMovie(models.Model):
    name = models.CharField(max_length=100, verbose_name='Nombre')
    is_active = models.BooleanField(default=True, verbose_name='Activa')

    def __str__(self):
        return self.name
    
class Movie(models.Model):
    title = models.CharField(max_length=255, verbose_name='Título')
    description = models.TextField(blank=True, verbose_name='Descripción')
    year = models.PositiveIntegerField(null=True, blank=True, verbose_name='Año')
    duration = models.PositiveIntegerField(null=True, blank=True, verbose_name='Duración (min)')
    
    poster = models.URLField(blank=True, verbose_name='Poster')
    backdrop = models.URLField(blank=True, verbose_name='Backdrop')

    trailer_url = models.URLField(blank=True, verbose_name='Trailer')
    stream_url = models.URLField(blank=True, null=True, verbose_name='URL de reproducción')

    is_hls = models.BooleanField(default=True, verbose_name='Es HLS')
    is_active = models.BooleanField(default=True, verbose_name='Activa')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado')
    
    external_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    source_url = models.URLField(blank=True, null=True)
    
    categories = models.ManyToManyField(
        CategoryMovie,
        related_name='movies',
        blank=True,
        verbose_name='Categorías'
    )

    def __str__(self):
        return self.title

class FavoriteMovie(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite_movies'
    )
    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')

class FavoriteChannel(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name='favorite_channels')
    channel = models.ForeignKey(Channel,on_delete=models.CASCADE,related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'channel')