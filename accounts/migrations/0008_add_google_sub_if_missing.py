from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_customuser_email_otp_code_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE corelink_identity_user "
                "ADD COLUMN IF NOT EXISTS google_sub varchar(255);"
                "CREATE UNIQUE INDEX IF NOT EXISTS corelink_identity_user_google_sub_uniq "
                "ON corelink_identity_user (google_sub) "
                "WHERE google_sub IS NOT NULL;"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS corelink_identity_user_google_sub_uniq;"
                "ALTER TABLE corelink_identity_user DROP COLUMN IF EXISTS google_sub;"
            ),
        ),
    ]
