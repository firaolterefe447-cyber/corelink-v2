# Generated migration to update Ethiopian language display names

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0031_alter_skill_context_companyinvitation"),
    ]

    operations = [
        migrations.AlterField(
            model_name='language',
            name='language_code',
            field=models.CharField(
                choices=[
                    ('am', 'Amharic'),
                    ('om', 'Afan Oromo'),
                    ('ti', 'Tigrinya'),
                    ('so', 'Somali'),
                    ('aa', 'Afar'),
                    ('sid', 'Sidamigna'),
                    ('wal', 'Wolayigna'),
                    ('gur', 'Gurage (General)'),
                    ('en', 'English'),
                    ('ar', 'Arabic'),
                    ('fr', 'French'),
                    ('es', 'Spanish'),
                    ('de', 'German'),
                    ('zh', 'Chinese'),
                    ('ja', 'Japanese'),
                    ('pt', 'Portuguese'),
                    ('ru', 'Russian'),
                    ('it', 'Italian'),
                    ('hi', 'Hindi'),
                    ('ko', 'Korean'),
                    ('tr', 'Turkish'),
                    ('fa', 'Persian'),
                    ('sw', 'Swahili'),
                    ('OTHER', 'Other (Custom)'),
                ],
                db_index=True,
                max_length=10,
                verbose_name='Language Code',
            ),
        ),
    ]
