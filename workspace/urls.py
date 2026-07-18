from django.urls import path
from . import views

urlpatterns = [
# Main Workspace/Portfolio URL
    path('network/right-now/', views.right_now_feed, name='right_now_feed'),
    path('update/<uuid:post_id>/', views.RightNowDetailView.as_view(), name='right_now_detail'),
    path('curation/', views.admin_curation_view, name='admin_curation'),

    # Message Admin & Support
    path('workspace/message-admin/', views.CompanyMessageCreateView.as_view(), name='company_message_admin'),
    path('support/messages/', views.CompanyMessageListView.as_view(), name='company_message_list'),
    path('support/message/<uuid:pk>/edit/', views.CompanyMessageUpdateView.as_view(), name='company_message_edit'),
    path('support/message/<uuid:pk>/delete/', views.CompanyMessageDeleteView.as_view(), name='company_message_delete'),

    # Messaging Hub
    path('workspace/messages/', views.chat_hub, name='chat_hub'),
    path('workspace/messages/<uuid:user_id>/', views.chat_hub, name='chat_with'),
    # Add this alongside your other chat URLs
    path('chat/delete/<uuid:message_id>/', views.delete_message, name='delete_message'),
]