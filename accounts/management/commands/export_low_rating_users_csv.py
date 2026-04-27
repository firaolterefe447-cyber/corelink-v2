import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Case, F, IntegerField, OrderBy, Q, Value, When

from accounts.models import CustomUser


class Command(BaseCommand):
    help = (
        "Export users with rating None or <= 3 to CSV with full name, phone number, "
        "telegram username, and rating."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="low_rating_users.csv",
            help="Output CSV path (default: low_rating_users.csv)",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output"])

        users = (
            CustomUser.objects
            .annotate(
                rating=Case(
                    When(role=CustomUser.Role.EXPERT, then=F("expert_profile__admin_rating")),
                    When(role=CustomUser.Role.VISIONARY, then=F("visionary_profile__admin_rating")),
                    When(role=CustomUser.Role.FOUNDER, then=F("founder_profile__admin_rating")),
                    default=Value(None),
                    output_field=IntegerField(),
                )
            )
            .filter(Q(rating__isnull=True) | Q(rating__lte=3))
            .order_by(OrderBy(F("rating"), nulls_first=True), "full_name")
            .values_list("full_name", "phone_number", "telegram_handle", "rating")
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["full_name", "phone_number", "telegram_username", "rating"])
            for full_name, phone_number, telegram_handle, rating in users:
                writer.writerow([
                    full_name,
                    phone_number,
                    telegram_handle or "",
                    "" if rating is None else rating,
                ])

        self.stdout.write(self.style.SUCCESS(f"Exported {users.count()} users to {output_path}"))
