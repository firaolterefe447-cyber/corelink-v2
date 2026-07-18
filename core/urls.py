from django.urls import path
from . import views

urlpatterns =[
    path("", views.index_view, name="home"),
    # Admin inspection views (transferred from operations)
    path('ops/pool/<str:pool_type>/', views.ops_pool_browser, name='ops_pool_browser'),
    path('ops/inspect/<uuid:user_id>/', views.inspect_user, name='inspect_user'),
    path('ops/toggle-verify/<uuid:user_id>/', views.toggle_verify, name='ops_toggle_verify'),
    path('ops/toggle-active/<uuid:user_id>/', views.toggle_active, name='ops_toggle_active'),
    path('ops/rate/<uuid:user_id>/<int:rating_value>/', views.update_rating, name='ops_update_rating'),
]