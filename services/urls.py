"""
Services App URL Configuration
"""

from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    # Public Service Detail
    path('p/<str:identifier>/service/<uuid:pk>/', views.service_detail_view, name='public_service_detail'),
    
    # Dashboard Services Management
    path('dashboard/services/', views.ServiceListView.as_view(), name='manage_services'),
    path('dashboard/services/new/', views.ServiceCreateView.as_view(), name='service_create'),
    path('dashboard/services/<uuid:pk>/edit/', views.ServiceUpdateView.as_view(), name='service_edit'),
    path('dashboard/services/<uuid:pk>/delete/', views.ServiceDeleteView.as_view(), name='service_delete'),
    
    # Service Gallery Management
    path('dashboard/services/<uuid:service_id>/gallery/', views.ServiceGalleryListView.as_view(), name='manage_service_gallery'),
    path('dashboard/services/<uuid:service_id>/gallery/new/', views.ServiceGalleryCreateView.as_view(), name='service_gallery_create'),
    path('dashboard/services/gallery/<uuid:pk>/edit/', views.ServiceGalleryUpdateView.as_view(), name='service_gallery_edit'),
    path('dashboard/services/gallery/<uuid:pk>/delete/', views.ServiceGalleryDeleteView.as_view(), name='service_gallery_delete'),
]
