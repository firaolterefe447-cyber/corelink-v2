from django.urls import path
from .views import (
    nexus_feed,
    NetworkPostCreateView,
    NetworkPostUpdateView,
    NetworkPostDeleteView,
    MyNetworkPostListView,
    NetworkPostDetailView,
    nexus_posts,
    company_nexus,
    right_now_feed,
    RightNowDetailView,
    admin_curation_view
)

urlpatterns = [
    # Main Feed
    path('', nexus_feed, name='nexus_feed'),
path('nexus/signals/', nexus_posts, name='nexus_posts'),
    path('discover/companies/', company_nexus, name='company_nexus'),
    # User's Posts
    path('my-broadcasts/', MyNetworkPostListView.as_view(), name='my_signals'),

    # CRUD Operations
    path('broadcast/', NetworkPostCreateView.as_view(), name='signal_create'),
    path('post/<uuid:pk>/', NetworkPostDetailView.as_view(), name='signal_detail'),
    path('<uuid:pk>/edit/', NetworkPostUpdateView.as_view(), name='signal_update'),
    path('<uuid:pk>/delete/', NetworkPostDeleteView.as_view(), name='signal_delete'),

    # Right Now Feed (moved from workspace)
    path('network/right-now/', right_now_feed, name='right_now_feed'),
    path('update/<uuid:post_id>/', RightNowDetailView.as_view(), name='right_now_detail'),
    path('curation/', admin_curation_view, name='admin_curation'),
]