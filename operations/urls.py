from django.urls import path
from . import views

urlpatterns =[
    path('pool/<str:pool_type>/', views.ops_pool_browser, name='ops_pool_browser'),
    path('inspect/<uuid:user_id>/', views.inspect_user, name='inspect_user'),
    path('toggle-verify/<uuid:user_id>/', views.toggle_verify, name='ops_toggle_verify'),
    path('toggle-active/<uuid:user_id>/', views.toggle_active, name='ops_toggle_active'),
    path('rate/<uuid:user_id>/<int:rating_value>/', views.update_rating, name='ops_update_rating'),
    path('approve/<str:model_type>/<uuid:item_id>/', views.toggle_cluster_item_status, name='ops_approve_item'),
    path('toggle-status/<str:model_type>/<uuid:item_id>/', views.toggle_cluster_item_status, name='ops_toggle_item_status'),
]