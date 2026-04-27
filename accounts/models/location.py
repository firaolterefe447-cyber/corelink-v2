from django.db import models
import uuid
from django.utils.text import slugify
class Country(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255, unique=True, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    # Branding
    logo = models.ImageField(upload_to="institutions/logos/", null=True, blank=True)
    cover_image = models.ImageField(upload_to="institutions/covers/", null=True, blank=True)

    # Content
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)

    # Metadata
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Country.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class City(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255, unique=True, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    # Branding
    logo = models.ImageField(upload_to="institutions/logos/", null=True, blank=True)
    cover_image = models.ImageField(upload_to="institutions/covers/", null=True, blank=True)

    # Content
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    Country = models.ForeignKey(
		"accounts.country",
		on_delete=models.CASCADE
	)
    # Metadata
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while City.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
