from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_alter_customuser_email_otp_code_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE corelink_identity_user "
                "ALTER COLUMN is_banned_from_right_now SET DEFAULT FALSE;"
                "ALTER TABLE corelink_identity_user "
                "ALTER COLUMN is_pinned_in_right_now SET DEFAULT FALSE;"
                "ALTER TABLE corelink_identity_user "
                "ALTER COLUMN is_hero_avatar_selected SET DEFAULT FALSE;"
                "ALTER TABLE corelink_identity_user "
                "ALTER COLUMN is_home_profile_selected SET DEFAULT FALSE;"
                "UPDATE corelink_identity_user SET is_banned_from_right_now = FALSE "
                "WHERE is_banned_from_right_now IS NULL;"
                "UPDATE corelink_identity_user SET is_pinned_in_right_now = FALSE "
                "WHERE is_pinned_in_right_now IS NULL;"
                "UPDATE corelink_identity_user SET is_hero_avatar_selected = FALSE "
                "WHERE is_hero_avatar_selected IS NULL;"
                "UPDATE corelink_identity_user SET is_home_profile_selected = FALSE "
                "WHERE is_home_profile_selected IS NULL;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
