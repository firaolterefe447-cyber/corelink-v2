# Generated migration for chat app
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('profiles', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyMessageToAdmin',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=150)),
                ('description', models.TextField(help_text='The long-form essay of your needs, vision, or challenges.')),
                ('status', models.CharField(choices=[('SUBMITTED', 'Submitted (Pending)'), ('REVIEWING', 'Admin Reviewing'), ('ACTIONING', 'Action in Progress'), ('RESOLVED', 'Resolved'), ('CLOSED', 'Closed')], db_index=True, default='SUBMITTED', max_length=20)),
                ('admin_notes', models.TextField(blank=True)),
                ('assigned_admin', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_company_messages', to=settings.AUTH_USER_MODEL)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='admin_messages', to='profiles.company')),
                ('founder', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='admin_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Message to Admin',
                'verbose_name_plural': 'Messages to Admin',
                'ordering': ['-created_at', 'title'],
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('body', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('is_read', models.BooleanField(default=False)),
                ('attachment', models.FileField(blank=True, null=True, upload_to='chat_attachments/%Y/%m/')),
                ('is_edited', models.BooleanField(default=False)),
                ('is_deleted', models.BooleanField(default=False)),
                ('receiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_messages', to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['timestamp'],
                'indexes': [
                    models.Index(fields=['sender', 'receiver'], name='chat_chatmessage_sender_receiver_idx'),
                ],
            },
        ),
    ]
