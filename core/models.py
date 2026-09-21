from pathlib import PurePosixPath
import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db.models.signals import post_delete
from django.db import models
from django.dispatch import receiver
from django.utils.text import get_valid_filename, slugify


def upload_public_file(instance, filename):
    """Store new uploads below the owning project's public directory.

    Existing ``PublicFile`` rows keep their current relative storage name. This
    function is only applied when Django receives a new uploaded file.
    """
    if not instance.project_id or not instance.project or not instance.project.slug:
        raise ValidationError(
            "Un PublicFile nuevo requiere un proyecto con slug antes de guardar el archivo."
        )

    project_slug = slugify(instance.project.slug)
    if project_slug != instance.project.slug:
        raise ValidationError("El slug del proyecto no es seguro para almacenamiento.")

    normalized_name = str(filename).replace("\\", "/")
    safe_name = get_valid_filename(PurePosixPath(normalized_name).name)
    if not safe_name or safe_name in {".", ".."}:
        raise ValidationError("El nombre del archivo no es válido.")

    return (PurePosixPath("public_files") / project_slug / safe_name).as_posix()

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    
class User(AbstractUser):

    email = models.EmailField(unique=True)
    roles = models.ManyToManyField(Role)
    email_verified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)    
    is_banned = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.id} | {self.email}"
    
class UserAuth(models.Model):
    PROVIDERS = (
        ("password", "Password"),
        ("google", "Google"),
        ("apple", "Apple"),
        ("facebook", "Facebook"),
    )

    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="auth_methods",)
    provider = models.CharField(max_length=20,choices=PROVIDERS,)

    provider_uid = models.CharField(max_length=255,blank=True,null=True,)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_uid"],
                name="unique_provider_uid",
            ),
            models.UniqueConstraint(
                fields=["user", "provider"],
                name="unique_user_provider",
            ),
        ]
        indexes = [
            models.Index(fields=["user"]),
        ]
        

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
            base_slug = slugify(base_name) or uuid.uuid4().hex
            self.slug = base_slug[:255]
            suffix = 2
            while (
                PublicFile.objects.filter(slug=self.slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                suffix_text = f"-{suffix}"
                self.slug = f"{base_slug[:255 - len(suffix_text)]}{suffix_text}"
                suffix += 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or self.file.name
    
    

@receiver(post_delete, sender=PublicFile)
def delete_public_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
