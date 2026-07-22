from django.urls import path
from .views import (
    nexus_feed,
    company_nexus,
    right_now_feed,
    RightNowDetailView,
    admin_curation_view
)

urlpatterns = [
    # Main Feed
    path('', nexus_feed, name='nexus_feed'),
    path('discover/companies/', company_nexus, name='company_nexus'),

    # Right Now Feed
    path('network/right-now/', right_now_feed, name='right_now_feed'),
    path('update/<uuid:post_id>/', RightNowDetailView.as_view(), name='right_now_detail'),
    path('curation/', admin_curation_view, name='admin_curation'),
]