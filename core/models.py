from django.db import models
from django.utils.text import slugify


class PublicFile(models.Model):
    file = models.FileField(upload_to="uploads/%Y/%m/")
    name = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    is_public = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_name = self.name or self.file.name
            self.slug = slugify(base_name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or self.file.name