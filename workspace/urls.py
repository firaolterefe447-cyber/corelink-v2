from django.urls import path
from . import views

urlpatterns = [
# Main Workspace/Portfolio URL
    path('network/right-now/', views.right_now_feed, name='right_now_feed'),
    path('update/<uuid:post_id>/', views.RightNowDetailView.as_view(), name='right_now_detail'),
    path('admin/curation/', views.admin_curation_view, name='admin_curation'),
    path('workspace/', views.workspace_view, name='collaboration_hub'),
    # Dashboards
    path('workspace/dashboard/', views.WorkspaceDashboardView.as_view(), name='workspace_dashboard'),
    path('workspace/founder/', views.FounderWorkspaceView.as_view(), name='founder_workspace'),
    path('workspace/visionary/actions/', views.visionary_action_page, name='visionary_action_page'),
    path('workspace/expert/actions/', views.expert_action_page, name='expert_action_page'),

    # Message Admin & Support
    path('workspace/message-admin/', views.CompanyMessageCreateView.as_view(), name='company_message_admin'),
    path('support/messages/', views.CompanyMessageListView.as_view(), name='company_message_list'),
    path('support/message/<uuid:pk>/edit/', views.CompanyMessageUpdateView.as_view(), name='company_message_edit'),
    path('support/message/<uuid:pk>/delete/', views.CompanyMessageDeleteView.as_view(), name='company_message_delete'),

    # Teams / Nexus
    path('teams/', views.team_nexus, name='team_nexus'),
    path('teams/create/', views.create_team_proposal, name='submit_team'),
    path('team/<slug:slug>/', views.team_detail, name='team_detail'),
    # Change this line in your urls.py:
    path('teams/<slug:slug>/manage/', views.manage_team, name='manage_team'),
    path('teams/<uuid:team_id>/join/', views.team_detail, name='join_team'),
    path('team/<slug:slug>/edit/', views.create_team_proposal, name='edit_team'),
    path('team/<slug:slug>/delete/', views.manage_team, name='delete_team'),





    # Messaging Hub
    path('workspace/messages/', views.chat_hub, name='chat_hub'),
    path('workspace/messages/<uuid:user_id>/', views.chat_hub, name='chat_with'),
    # Add this alongside your other chat URLs
    path('chat/delete/<uuid:message_id>/', views.delete_message, name='delete_message'),
    # Waitlist / Preferences
    path('workspace/waitlist/apply/', views.PreferenceApplicationCreateView.as_view(),
         name='submit_preference_application'),
    path('workspace/waitlist/<uuid:pk>/edit/', views.PreferenceApplicationUpdateView.as_view(), name='edit_preference'),
    path('workspace/waitlist/<uuid:pk>/delete/', views.PreferenceApplicationDeleteView.as_view(),
         name='delete_preference'),

    # Direct Connection Requests
    path('workspace/connect/request/', views.ConnectionRequestCreateView.as_view(), name='submit_connection_request'),
    path('workspace/connect/<uuid:pk>/edit/', views.ConnectionRequestUpdateView.as_view(), name='edit_request'),
    path('workspace/connect/<uuid:pk>/delete/', views.ConnectionRequestDeleteView.as_view(), name='delete_request'),
]