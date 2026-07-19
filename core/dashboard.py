# core/dashboard.py
from django.utils.translation import gettext_lazy as _
from accounts.models import CustomUser, ApplicationRequest, CommunityContributor

def dashboard_callback(request, context):
    # 1. Calculate Stats
    total_users = CustomUser.objects.count()
    experts = CustomUser.objects.filter(role="EXPERT").count()
    pending_apps = ApplicationRequest.objects.filter(status="PENDING").count()
    volunteers = CommunityContributor.objects.filter(is_contacted=False).count()

    context.update({
        "kpi": [
            {
                "title": _("Total Network"),
                "metric": total_users,
                "chart": [experts, total_users],
            },
            {
                "title": _("Experts"),
                "metric": experts,
                "metric_class": "text-emerald-600",
                "footer": _("Verified Talent"),
            },
            {
                "title": _("Pending Applications"),
                "metric": pending_apps,
                "metric_class": "text-amber-600",
                "footer": _("Requires Review"),
            },
        ],
        "navigation": [
            {
                "title": _("Review Applications"),
                "link": "/admin/accounts/applicationrequest/?status__exact=PENDING",
                "icon": "inventory",
            },
            {
                "title": _("System Settings"),
                "link": "/admin/accounts/customuser/",
                "icon": "settings",
            },
        ]
    })
    return context


from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.utils import timezone
from datetime import timedelta

# Import your CustomUser from the accounts app
from accounts.models import CustomUser


def dashboard_callback(request, context):
    """
    Configured in settings.py as 'DASHBOARD_CALLBACK': 'core.dashboard.dashboard_callback'
    """

    # 1. Get Total Users
    total_users = CustomUser.objects.count()

    # 2. Get Verified Users (for the footer text)
    verified_count = CustomUser.objects.filter(is_verified=True).count()

    # 3. Get Data for the Chart (Last 7 Days)
    last_7_days = timezone.now() - timedelta(days=7)

    # Group users by day joined
    recent_stats = (
        CustomUser.objects.filter(date_joined__gte=last_7_days)
        .annotate(day=TruncDay('date_joined'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    # Format data for Unfold Chart [[ "Day", Value ], ...]
    chart_data = [
        [day_stat['day'].strftime("%d %b"), day_stat['count']]
        for day_stat in recent_stats
    ]

    # 4. Update the context with the KPI card
    context.update({
        "kpi": [
            {
                "title": _("Total Users"),
                "metric": total_users,
                # This creates a small line chart inside the card
                "chart": chart_data,
                "footer": format_html(
                    '<strong class="text-green-600">{}</strong> Verified Accounts',
                    verified_count
                ),
            },
            # You can add more cards here (e.g., Total Applications)
        ]
    })

    return context