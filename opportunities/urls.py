from django.urls import path
from . import views

app_name = 'opportunities'

urlpatterns =[
    # Public Discovery (Feed & Search)
    path('', views.OpportunityFeedView.as_view(), name='feed'),
path('post-job/', views.PublicOpportunityCreateView.as_view(), name='public_post'),
    # Map UUID first for old unmigrated jobs, then Slug for new jobs
    path('job/<uuid:pk>/', views.OpportunityDetailView.as_view(), name='detail_pk'),
    path('job/<slug:slug>/', views.OpportunityDetailView.as_view(), name='detail'),
    path('job/<slug:slug>/og-image/', views.opportunity_og_image, name='og_image'),

    # Actions (Apply / Scout)
    path('job/<uuid:pk>/apply/', views.link_profile_action, name='apply_pk'),
    path('job/<slug:slug>/apply/', views.link_profile_action, name='apply'),

    path('job/<uuid:pk>/visit/', views.track_external_application, name='visit_external_pk'),
    path('job/<slug:slug>/visit/', views.track_external_application, name='visit_external'),

    # ==========================================
    # 3. CREATOR WORKSPACE (Manage Posts)
    # ==========================================
    path('workspace/', views.WorkspaceOpportunityListView.as_view(), name='workspace_list'),
    path('workspace/create/', views.OpportunityCreateView.as_view(), name='create'),

    path('workspace/job/<uuid:pk>/edit/', views.OpportunityUpdateView.as_view(), name='update_pk'),
    path('workspace/job/<slug:slug>/edit/', views.OpportunityUpdateView.as_view(), name='update'),

    path('workspace/job/<uuid:pk>/delete/', views.OpportunityDeleteView.as_view(), name='delete_pk'),
    path('workspace/job/<slug:slug>/delete/', views.OpportunityDeleteView.as_view(), name='delete'),

    # Recruiter Pipeline (Manage Applicants)
    path('workspace/job/<uuid:pk>/pipeline/', views.ApplicantBoardView.as_view(), name='applicant_board_pk'),
    path('workspace/job/<slug:slug>/pipeline/', views.ApplicantBoardView.as_view(), name='applicant_board'),

    path('workspace/application/<uuid:application_id>/inspect/', views.inspect_applicant_profile, name='inspect_profile'),
    path('workspace/application/<uuid:application_id>/update/', views.update_application_status, name='update_status'),

    # ==========================================
    # 5. INDIVIDUAL USER JOB MANAGEMENT (New System)
    # ==========================================
    path('my-jobs/', views.UserJobManagementView.as_view(), name='user_job_management'),
    path('my-jobs/create/', views.UserJobCreateView.as_view(), name='user_job_create'),
    path('my-jobs/<slug:slug>/edit/', views.UserJobUpdateView.as_view(), name='user_job_update'),
    path('my-jobs/<slug:slug>/delete/', views.UserJobDeleteView.as_view(), name='user_job_delete'),
    path('my-jobs/<slug:slug>/applicants/', views.UserApplicantBoardView.as_view(), name='user_applicant_board'),
]