"""
Core Application Models

This module defines the primary data structures for the platform's business logic,
team management, marketplace supply systems, and communications.
"""
import os
import logging
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from profiles.models import Company

logger = logging.getLogger(__name__)

# Company Messages to Admin

class CompanyMessageToAdmin(TimeStampedModel):
    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', _('Submitted (Pending)')
        REVIEWING = 'REVIEWING', _('Admin Reviewing')
        ACTIONING = 'ACTIONING', _('Action in Progress')
        RESOLVED = 'RESOLVED', _('Resolved')
        CLOSED = 'CLOSED', _('Closed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='admin_messages')
    founder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_messages')

    # Content
    title = models.CharField(max_length=150)
    description = models.TextField(help_text="The long-form essay of your needs, vision, or challenges.")

    # Admin Tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    admin_notes = models.TextField(blank=True)
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_company_messages'
    )

    class Meta:
        verbose_name = _("Message to Admin")
        verbose_name_plural = _("Messages to Admin")
        ordering = ['-created_at', 'title']

    def __str__(self):
        return f"{self.title} - {self.company.name} ({self.get_status_display()})"


# Communications / Chat

class ChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages', on_delete=models.CASCADE)

    body = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)  # Indexed for sorting
    is_read = models.BooleanField(default=False)
    # 1. ADDITIVE FIELDS (Safe for live users)
    attachment = models.FileField(upload_to='chat_attachments/%Y/%m/', blank=True, null=True)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    # Smart Properties
    @property
    def is_image(self):
        if not self.attachment:
            return False
        ext = os.path.splitext(self.attachment.name)[1].lower()
        return ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']


    @property
    def filename(self):
        if self.attachment:
            return os.path.basename(self.attachment.name)
        return None
    class Meta:
        ordering = ['timestamp']
        indexes =[
            models.Index(fields=['sender', 'receiver']),
        ]

    def __str__(self):
        return f"Message {self.id} from {self.sender} to {self.receiver}"