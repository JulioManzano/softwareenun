from django.db import models
from django.utils.text import slugify
import uuid

def upload_public_file(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    filename = f"{uuid.uuid4()}.{extension}" if extension else str(uuid.uuid4())

    return f"uploads/{filename}"

class PublicFileProject(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class PublicFile(models.Model):
    project = models.ForeignKey(PublicFileProject,on_delete=models.CASCADE,related_name="files", null=True,
    blank=True,)
    file = models.FileField(upload_to=upload_public_file)
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