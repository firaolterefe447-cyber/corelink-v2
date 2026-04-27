from django.db import migrations


def backfill_first_last_name(apps, schema_editor):
    CustomUser = apps.get_model("accounts", "CustomUser")

    users = CustomUser.objects.filter(full_name__isnull=False).exclude(full_name__exact="")

    for user in users.iterator():
        first_name = (user.first_name or "").strip()
        last_name = (user.last_name or "").strip()

        if first_name or last_name:
            continue

        normalized_full_name = (user.full_name or "").strip()
        if not normalized_full_name:
            continue

        name_parts = normalized_full_name.split()
        user.first_name = name_parts[0]
        user.last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        user.save(update_fields=["first_name", "last_name"])


def reverse_backfill_first_last_name(apps, schema_editor):
    CustomUser = apps.get_model("accounts", "CustomUser")
    users = CustomUser.objects.filter(full_name__isnull=True) | CustomUser.objects.filter(full_name__exact="")

    for user in users.iterator():
        first_name = (user.first_name or "").strip()
        last_name = (user.last_name or "").strip()
        combined_name = f"{first_name} {last_name}".strip()

        if combined_name:
            user.full_name = combined_name
            user.save(update_fields=["full_name"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0014_customuser_city_customuser_country"),
    ]

    operations = [
        migrations.RunPython(backfill_first_last_name, reverse_backfill_first_last_name),
    ]
