from django.urls import path
from .views import (
    nexus_feed,
    NetworkPostCreateView,
    NetworkPostUpdateView,
    NetworkPostDeleteView,
    MyNetworkPostListView,
    NetworkPostDetailView,
    nexus_posts
)

urlpatterns = [
    # Main Feed
    path('', nexus_feed, name='nexus_feed'),
path('nexus/signals/', nexus_posts, name='nexus_posts'),

    # User's Posts
    path('my-broadcasts/', MyNetworkPostListView.as_view(), name='my_signals'),

    # CRUD Operations
    path('broadcast/', NetworkPostCreateView.as_view(), name='signal_create'),
    path('post/<uuid:pk>/', NetworkPostDetailView.as_view(), name='signal_detail'),
    path('<uuid:pk>/edit/', NetworkPostUpdateView.as_view(), name='signal_update'),
    path('<uuid:pk>/delete/', NetworkPostDeleteView.as_view(), name='signal_delete'),
]