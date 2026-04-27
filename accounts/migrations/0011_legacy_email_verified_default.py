from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_legacy_user_defaults"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE corelink_identity_user "
                "ALTER COLUMN email_verified SET DEFAULT FALSE;"
                "UPDATE corelink_identity_user SET email_verified = FALSE "
                "WHERE email_verified IS NULL;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
