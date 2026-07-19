"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CORELINK UNIFIED PORTFOLIO URLS                           ║
║                    Clean, RESTful, and Highly Scalable Routing               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from django.urls import path
from . import views
from .views import ServiceDetailView

urlpatterns = [
    # ==========================================
    # --- 1. PUBLIC PROFILES & ROUTING ---
    # ==========================================
    # Handles User Slugs, Company Slugs, and CoreLink IDs dynamically
    path('p/<str:identifier>/', views.public_profile_view, name='public_profile'),
    path('p/<str:identifier>/og-image/', views.profile_og_image, name='profile_og_image'),
    path('p/<str:identifier>/project/<uuid:pk>/', views.project_detail_view, name='public_project_detail'),
    path('p/<str:identifier>/service/<uuid:pk>/', views.service_detail_view, name='public_service_detail'),
    # Optional explicitly routed company profile (kept for backward compatibility)
    path('p/company/<slug:slug>/', views.company_public_profile, name='company_public_profile'),

    # ==========================================
    # --- 2. DASHBOARD & MAIN LOBBY ---
    # ==========================================
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path('dashboard/settings/', views.ProfileSettingsView.as_view(), name='profile_settings'),

    # Global Media & Visuals (Avatars & Covers)
    path('dashboard/media/', views.IdentityMediaView.as_view(), name='media_manager'),
    path('dashboard/media/delete/<str:asset_type>/', views.delete_media_asset, name='media_delete'),

    # ==========================================
    # --- 3. UNIFIED PORTFOLIO BUILDER (LEGO BLOCKS) ---
    # ==========================================

    # A. Professional Roles (Headlines)
    path('dashboard/headlines/', views.HeadlineListView.as_view(), name='manage_headlines'),
    path('dashboard/headlines/new/', views.HeadlineCreateView.as_view(), name='headline_create'),
    path('dashboard/headlines/<uuid:pk>/edit/', views.HeadlineUpdateView.as_view(), name='headline_edit'),
    path('dashboard/headlines/<uuid:pk>/delete/', views.HeadlineDeleteView.as_view(), name='headline_delete'),

    # B. Skills & Tools
    path('dashboard/skills/', views.SkillListView.as_view(), name='manage_skills'),
    path('dashboard/skills/new/', views.SkillCreateView.as_view(), name='skill_create'),
    path('dashboard/skills/<uuid:pk>/edit/', views.SkillUpdateView.as_view(), name='skill_edit'),
    path('dashboard/skills/<uuid:pk>/delete/', views.SkillDeleteView.as_view(), name='skill_delete'),

    # C. Work Experience
    path('dashboard/experience/', views.ExperienceListView.as_view(), name='manage_experiences'),
    path('dashboard/experience/new/', views.ExperienceCreateView.as_view(), name='experience_create'),
    path('dashboard/experience/<uuid:pk>/edit/', views.ExperienceUpdateView.as_view(), name='experience_edit'),
    path('dashboard/experience/<uuid:pk>/delete/', views.ExperienceDeleteView.as_view(), name='experience_delete'),

    # D. Education & Credentials
    path('dashboard/credentials/', views.CredentialListView.as_view(), name='manage_credentials'),
    path('dashboard/credentials/new/', views.CredentialCreateView.as_view(), name='credential_create'),
    path('dashboard/credentials/<uuid:pk>/edit/', views.CredentialUpdateView.as_view(), name='credential_edit'),
    path('dashboard/credentials/<uuid:pk>/delete/', views.CredentialDeleteView.as_view(), name='credential_delete'),

    # E. Portfolio Projects
    path('dashboard/projects/', views.ProjectListView.as_view(), name='manage_projects'),
    path('dashboard/projects/guide/', views.project_creation_guide, name='project_guide'),
    path('dashboard/projects/new/', views.ProjectCreateView.as_view(), name='project_create'),
    path('dashboard/projects/<uuid:pk>/edit/', views.ProjectUpdateView.as_view(), name='project_edit'),
    path('dashboard/projects/<uuid:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    path('api/projects/auto-detect-category/', views.auto_detect_project_category, name='auto_detect_project_category'),
path('api/right-now/create/', views.api_create_right_now, name='api_create_right_now'),
    # F. Content, Diaries, and Vision Blocks
    path('dashboard/posts/', views.ContentPostListView.as_view(), name='manage_contents'),
    path('dashboard/posts/new/', views.ContentPostCreateView.as_view(), name='content_create'),
    path('dashboard/posts/<uuid:pk>/edit/', views.ContentPostUpdateView.as_view(), name='content_edit'),
    path('dashboard/posts/<uuid:pk>/delete/', views.ContentPostDeleteView.as_view(), name='content_delete'),
    path('dashboard/right-now/', views.RightNowListView.as_view(), name='manage_right_now'),
    path('dashboard/right-now/new/', views.RightNowCreateView.as_view(), name='right_now_create'),
    path('dashboard/right-now/<uuid:pk>/edit/', views.RightNowUpdateView.as_view(), name='right_now_edit'),
    path('dashboard/right-now/<uuid:pk>/delete/', views.RightNowDeleteView.as_view(), name='right_now_delete'),
    # G. Job & Collaboration Preferences
    path('dashboard/preferences/', views.PreferenceListView.as_view(), name='manage_preferences'),
    path('dashboard/preferences/new/', views.PreferenceCreateView.as_view(), name='preference_create'),
    path('dashboard/preferences/<uuid:pk>/edit/', views.PreferenceUpdateView.as_view(), name='preference_edit'),
    path('dashboard/preferences/<uuid:pk>/delete/', views.PreferenceDeleteView.as_view(), name='preference_delete'),

    # H. Languages
    path('dashboard/languages/', views.LanguageListView.as_view(), name='language_list'),
    path('dashboard/languages/new/', views.LanguageCreateView.as_view(), name='language_create'),
    path('dashboard/languages/<uuid:pk>/edit/', views.LanguageUpdateView.as_view(), name='language_edit'),
    path('dashboard/languages/<uuid:pk>/delete/', views.LanguageDeleteView.as_view(), name='language_delete'),

    # I. User Services (distinct from Company Services)
    path('dashboard/services/', views.ServiceListView.as_view(), name='manage_services'),
    path('dashboard/services/new/', views.ServiceCreateView.as_view(), name='service_create'),
    path('dashboard/services/<uuid:pk>/edit/', views.ServiceUpdateView.as_view(), name='service_edit'),
    path('dashboard/services/<uuid:pk>/delete/', views.ServiceDeleteView.as_view(), name='service_delete'),
    path('dashboard/services/<uuid:service_id>/gallery/', views.ServiceGalleryListView.as_view(), name='manage_service_gallery'),
    path('dashboard/services/<uuid:service_id>/gallery/new/', views.ServiceGalleryCreateView.as_view(), name='service_gallery_create'),
    path('dashboard/services/gallery/<uuid:pk>/edit/', views.ServiceGalleryUpdateView.as_view(), name='service_gallery_edit'),
    path('dashboard/services/gallery/<uuid:pk>/delete/', views.ServiceGalleryDeleteView.as_view(), name='service_gallery_delete'),

    # I. Live Opportunities (The 10x Feature)
    path('dashboard/opportunities/', views.OpportunityListView.as_view(), name='manage_opportunities'),
    path('dashboard/opportunities/new/', views.OpportunityCreateView.as_view(), name='opportunity_create'),
    path('dashboard/opportunities/<uuid:pk>/edit/', views.OpportunityUpdateView.as_view(), name='opportunity_edit'),
    path('dashboard/opportunities/<uuid:pk>/delete/', views.OpportunityDeleteView.as_view(), name='opportunity_delete'),

    # ==========================================
    # --- 4. NETWORK & CONTACTS ---
    # ==========================================
# The Engagement APIs
    path('api/right-now/<uuid:post_id>/toggle-like/', views.api_toggle_like, name='api_toggle_like'),
    path('api/right-now/<uuid:post_id>/add-comment/', views.api_add_comment, name='api_add_comment'),
    path('api/right-now/<uuid:post_id>/comments/', views.api_get_comments, name='api_get_comments'),
    path('api/oracle-score/', views.api_get_oracle_score, name='api_get_oracle_score'),
    # The Network Dashboard (Shows both Contacts & Socials)
    path('dashboard/network/', views.NetworkListView.as_view(), name='manage_network'),

    # Social Links CRUD
    path('dashboard/network/social/new/', views.SocialCreateView.as_view(), name='social_create'),
    path('dashboard/network/social/<uuid:pk>/edit/', views.SocialUpdateView.as_view(), name='social_edit'),
    path('dashboard/network/social/<uuid:pk>/delete/', views.SocialDeleteView.as_view(), name='social_delete'),

    # Contact Methods CRUD
    path('dashboard/network/contact/new/', views.ContactCreateView.as_view(), name='contact_create'),
    path('dashboard/network/contact/<uuid:pk>/edit/', views.ContactUpdateView.as_view(), name='contact_edit'),
    path('dashboard/network/contact/<uuid:pk>/delete/', views.ContactDeleteView.as_view(), name='contact_delete'),

    # ==========================================
    # --- 5. ENTERPRISE / COMPANY CMS ---
    # ==========================================

    # Company Onboarding
    path('company/onboarding/', views.company_create, name='company_create'),
    # Company Core
    path('company/<slug:slug>/manage/', views.CompanyDashboardView.as_view(), name='company_admin_dashboard'),
    path('company/<slug:slug>/edit/', views.CompanyEditView.as_view(), name='company_edit'),

    # Team Management
    path('company/<slug:slug>/team/', views.company_team_manage, name='company_team_manage'),
    path('company/<slug:slug>/team/invite/', views.company_team_invite, name='company_team_invite'),
    path('company/<slug:slug>/team/<uuid:member_id>/edit/', views.company_team_edit, name='company_team_edit'),
    path('company/<slug:slug>/team/<uuid:member_id>/remove/', views.company_team_remove, name='company_team_remove'),
    path('api/search-user/', views.search_user_for_invitation, name='search_user_for_invitation'),
    
    # Invitation Accept/Decline
    path('invitation/<uuid:invitation_id>/accept/', views.accept_company_invitation, name='accept_company_invitation'),
    path('invitation/<uuid:invitation_id>/decline/', views.decline_company_invitation, name='decline_company_invitation'),

    # Company Services
    path('dashboard/company/services/', views.CompanyServiceListView.as_view(), name='manage_company_services'),
    path('dashboard/company/services/new/', views.CompanyServiceCreateView.as_view(), name='company_service_create'),
    path('dashboard/company/services/<uuid:pk>/edit/', views.CompanyServiceUpdateView.as_view(), name='company_service_edit'),
    path('dashboard/company/services/<uuid:pk>/delete/', views.CompanyServiceDeleteView.as_view(), name='company_service_delete'),

    # Company News
    path('dashboard/company/news/', views.NewsListView.as_view(), name='manage_news_list'),
    path('dashboard/company/news/create/', views.NewsCreateView.as_view(), name='news_create'),
    path('dashboard/company/news/<slug:slug>/edit/', views.NewsUpdateView.as_view(), name='news_edit'),
    path('dashboard/company/news/<slug:slug>/delete/', views.NewsDeleteView.as_view(), name='news_delete'),

    # Public News Detail
    path('news/<slug:slug>/', views.NewsDetailView.as_view(), name='news_detail'),

    # Company Timeline / Milestones
    path('dashboard/company/timeline/', views.MilestoneListView.as_view(), name='manage_milestones'),
    path('dashboard/company/timeline/new/', views.MilestoneCreateView.as_view(), name='milestone_create'),
    path('dashboard/company/timeline/<uuid:pk>/edit/', views.MilestoneUpdateView.as_view(), name='milestone_edit'),
    path('dashboard/company/timeline/<uuid:pk>/delete/', views.MilestoneDeleteView.as_view(), name='milestone_delete'),
    # Tiny API Endpoint for Command Center
    path('company/<slug:slug>/quick-update/', views.company_quick_update, name='company_quick_update'),

    # Media API Endpoint (Already in views, just adding the route)
    path('company/<slug:slug>/media/', views.company_media_manage, name='company_media_manage'),
path('service/<uuid:pk>/', ServiceDetailView.as_view(), name='public_service_detail'),
    # Company Network/Contacts
    path('company/network/', views.ManageCompanyNetworkView.as_view(), name='manage_company_network'),
    path('company/contact/add/', views.CompanyContactCreateView.as_view(), name='company_contact_create'),
    path('company/contact/<uuid:pk>/edit/', views.CompanyContactUpdateView.as_view(), name='company_contact_update'),
    path('company/social/add/', views.CompanySocialCreateView.as_view(), name='company_social_create'),
    path('company/social/<uuid:pk>/edit/', views.CompanySocialUpdateView.as_view(), name='company_social_update'),
]