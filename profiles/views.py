"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CORELINK UNIFIED PORTFOLIO VIEWS                          ║
║                    Zero-Loss, High-Performance, Secure                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
This module serves as the central nervous system for CoreLink's Unified Profiles.
It handles user portfolios, public routing, company management, and media assets.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 0. SYSTEM IMPORTS & DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════════
import logging
import json
from django.utils.text import slugify
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, JsonResponse
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.db.models import Q

# Custom Models & Forms
from accounts.models import CustomUser, UniversalSocialLink, UniversalContactMethod
from profiles.models.new_unified_profile import (
    UserProfile, ProfileHeadline, Skill, Credential, PortfolioProject,
    ProjectGallery, WorkExperience, ContentPost, UnifiedJobPreference, LiveOpportunity,
    RightNowPost, RightNowMedia, RightNowLike, RightNowComment, Language
)
from profiles.models import (
    Company, CompanyMember, CompanyService, ServiceGalleryImage,
    CompanyNews, NewsGalleryImage, CompanyMilestone, CompanySocialLink, CompanyContactMethod, CompanyInvitation
)
from profiles.forms import (
    UserProfileForm, ProfileHeadlineForm, SkillForm, CredentialForm, PortfolioProjectForm,
    WorkExperienceForm, ContentPostForm, JobPreferenceForm, LiveOpportunityForm,
    CompanyProfileUpdateForm, CompanyServiceForm, CompanyNewsForm, CompanyMilestoneForm,
    CompanySocialLinkForm, CompanyContactMethodForm, SocialLinkForm, ContactMethodForm,
    IdentityMediaForm, AddCompanyMemberForm, RightNowPostForm, LanguageForm
)

logger = logging.getLogger(__name__)


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║ CLUSTER 1: CORE SECURITY & ARCHITECTURE MIXINS                             ║
# ║ Human Context: These mixins form the bedrock of our security and UX. They  ║
# ║ ensure users can never modify someone else's data, handle dynamic form     ║
# ║ routing, and auto-attach portfolios to new records silently.               ║
# ╚════════════════════════════════════════════════════════════════════════════╝

class RoleAwareFormMixin:
    """Injects the request.user into the form so it dynamically adapts to roles."""
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class PortfolioSecurityMixin(LoginRequiredMixin):
    """Locks queries so users can only ever view/edit/delete their own portfolio blocks."""
    def get_queryset(self):
        return self.model.objects.filter(profile__user=self.request.user)

class ContentPostSuccessUrlMixin:
    """Dynamically returns the success URL based on the saved object's post_type."""
    def get_success_url(self):
        post_type = self.object.post_type

        # Note: Replace the strings inside reverse() with the ACTUAL names
        # you defined in your urls.py for those list views.
        if post_type == 'GROWTH_LOG':
            return reverse('manage_growth_logs')
        elif post_type == 'VISION_BLOCK':
            return reverse('manage_vision_blocks')
        elif post_type == 'ESSAY':
            return reverse('manage_essays')

        # Fallback just in case
        return reverse('manage_contents')

class PortfolioCreateMixin:
    """Automatically attaches the user's portfolio to the object being created."""
    def form_valid(self, form):
        # 1. Get or create the user's profile
        portfolio, _ = UserProfile.objects.get_or_create(user=self.request.user)
        # 2. Attach the profile to the form instance before saving
        form.instance.profile = portfolio
        messages.success(self.request, "Added successfully.")
        response = super().form_valid(form)
        # 3. TRANSACTION-SAFE: Queue Oracle update after transaction commits
        from profiles.automatic_rating import CoreLinkOracle
        try:
            transaction.on_commit(lambda: CoreLinkOracle.update_user_rating(self.request.user.id))
            logger.info(f"[ORACLE QUEUED] Oracle update queued for user {self.request.user.id} after creating {form.instance.__class__.__name__}")
        except Exception as e:
            logger.error(f"[ORACLE QUEUED] Failed to queue update for user {self.request.user.id}: {str(e)}", exc_info=True)
        return response


class OracleUpdateMixin:
    """
    TRANSACTION-SAFE FALLBACK: Queues Oracle update after any profile modification.
    This ensures scores update even if Django signals fail to fire, while respecting DB locks.
    """
    def form_valid(self, form):
        response = super().form_valid(form)
        # Queue Oracle update after transaction commits (prevents race conditions)
        from profiles.automatic_rating import CoreLinkOracle
        try:
            user_id = self.request.user.id
            transaction.on_commit(lambda: CoreLinkOracle.update_user_rating(user_id))
            logger.info(f"[ORACLE QUEUED] Oracle update queued for user {user_id} after updating {form.instance.__class__.__name__}")
        except Exception as e:
            logger.error(f"[ORACLE QUEUED] Failed to queue update for user {self.request.user.id}: {str(e)}", exc_info=True)
        return response

class CompanyContextMixin(LoginRequiredMixin):
    """Fetches the user's active company and ensures they are an OWNER or ADMIN."""
    def get_company(self):
        membership = self.request.user.company_memberships.filter(
            is_active=True, role__in=['OWNER', 'ADMIN']
        ).select_related('company').first()

        if not membership:
            raise PermissionDenied("You do not have administrative access to an active company.")
        return membership.company

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company'] = self.get_company()
        return context


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║ CLUSTER 2: THE ROUTING HUB (DASHBOARD & PUBLIC)                            ║
# ║ Human Context: The Grand Central Station of the app. This determines what  ║
# ║ a user sees when they log in, and how the outside world views their profile.║
# ╚════════════════════════════════════════════════════════════════════════════╝

@login_required
def dashboard_view(request):
    """
    The Unified Command Center.
    Loads the user's complete portfolio and company data (if applicable) for the dashboard.
    """
    user = CustomUser.objects.prefetch_related('social_links', 'contact_methods').get(pk=request.user.pk)

    # 1. Ensure Portfolio exists and prefetch all related blocks to prevent N+1 query issues
    portfolio, created = UserProfile.objects.prefetch_related(
        'headlines', 'skills', 'credentials', 'projects__gallery',
        'experiences', 'content_posts', 'job_preferences', 'live_opportunities'
    ).get_or_create(user=user)
    
    # Ensure slug is generated for new portfolios
    if created and not portfolio.slug:
        portfolio.save()

    # 2. Fetch Founder/Company Data if the user is a Founder
    company_data = None
    if user.role == 'FOUNDER':
        membership = user.company_memberships.filter(is_active=True).select_related('company').first()
        company_data = membership.company if membership else None

    context = {
        'user': user,
        'portfolio': portfolio,
        'company': company_data,
        'headlines': portfolio.headlines.all(),
        'skills': portfolio.skills.all(),
        'credentials': portfolio.credentials.all(),
        'projects': portfolio.projects.all(),
        'experiences': portfolio.experiences.all().order_by('-is_current', '-start_date'),
        'posts': portfolio.content_posts.all(),
        'opportunities': portfolio.live_opportunities.filter(is_active=True),
        'preferences': portfolio.job_preferences.all(),
        # THIS IS THE NEW PART:
        'growth_logs': portfolio.content_posts.filter(post_type='GROWTH_LOG')[:2],
        'essays': portfolio.content_posts.filter(post_type='ESSAY')[:2],
        'vision_blocks': portfolio.content_posts.filter(post_type='VISION_BLOCK')[:2],

        'opportunities': portfolio.live_opportunities.filter(is_active=True),
        'preferences': portfolio.job_preferences.all(),

    }
    return render(request, 'dashboard/main_dashboard.html', context)


def public_profile_view(request, identifier):
    """
    Universal Profile Router.
    Routes identifiers to Company pages or Unified User Portfolios.
    """
    try:
        # 1. Check for Company Slug
        company = Company.objects.filter(slug=identifier).first()
        if company:
            return company_public_profile(request, slug=company.slug)

        # 2. Check for Unified Portfolio Slug
        target_user = None
        portfolio = UserProfile.objects.filter(slug=identifier).first()

        if portfolio:
            target_user = portfolio.user
        else:
            # 3. Fallback: Search by CoreLink ID (e.g., VIS-2024-001)
            target_user = get_object_or_404(CustomUser, corelink_id=identifier)

            # SEO Redirect: If found by ID, force-redirect to their proper Slug
            found_slug = getattr(target_user.portfolio, 'slug', None) if hasattr(target_user, 'portfolio') else None
            if found_slug:
                return redirect('public_profile', identifier=found_slug)

        # 4. Gather Data (Founder Routing Block skipped to allow personal portfolios)
        if not hasattr(target_user, 'portfolio'):
            raise Http404("Profile not found.")

        profile = target_user.portfolio
        contact_methods = UniversalContactMethod.objects.filter(user=target_user).order_by('-created_at')
        social_links = UniversalSocialLink.objects.filter(user=target_user).order_by('order')

        # Get projects and annotate with PDF-only status
        projects = profile.projects.all().prefetch_related('gallery')
        for project in projects:
            valid_assets = project.gallery.all()
            project.all_pdfs = False
            if valid_assets.exists():
                project.all_pdfs = all(asset.asset_type == 'DOCUMENT' for asset in valid_assets)

        # 5. Build Context with Modular Blocks
        context = {
            'profile': profile,
            'user': target_user,
            'role_title': target_user.get_role_display(),

            # Infrastructure
            'contact_methods': contact_methods,
            'social_links': social_links,

            # Identity Blocks
            'headlines': profile.headlines.all(),
            'skills': profile.skills.all(),
            'languages': profile.languages.all(),
            'credentials': profile.credentials.all().order_by('-issue_date'),
            'experiences': profile.experiences.all().order_by('-is_current', '-start_date'),

            # Assets & Content
            'projects': projects,
            'content_posts': profile.content_posts.filter(visibility='PUBLIC'),
            'essays': profile.content_posts.filter(visibility='PUBLIC', post_type='ESSAY').order_by('-created_at'),
            'vision_blocks': profile.content_posts.filter(visibility='PUBLIC', post_type='VISION_BLOCK').order_by('-created_at'),
            'progress_logs': profile.content_posts.filter(visibility='PUBLIC').exclude(post_type__in=['VISION_BLOCK', 'ESSAY']).order_by('-created_at'),

            # 🔥 THE NEW FOCUS HISTORY FEED
            'right_now_posts': profile.right_now_posts.filter(
                is_published=True
            ).prefetch_related('gallery').order_by('-created_at'),

            # Intent & 10X Opportunities
            'job_preferences': profile.job_preferences.filter(is_active=True),
            'live_opportunities': profile.live_opportunities.filter(
                is_active=True,
                expires_at__gt=timezone.now()
            )
        }

        return render(request, 'profiles/public_portfolio.html', context)

    except Exception as e:
        logger.error(f"Error loading profile for identifier '{identifier}': {str(e)}", exc_info=True)
        raise


def project_detail_view(request, identifier, pk):
    """
    Public Project Detail View.
    Shows full project information including gallery, problem statement, solution, and description.
    """
    # Get the user profile from identifier (slug or CoreLink ID)
    target_user = None
    portfolio = UserProfile.objects.filter(slug=identifier).first()
    
    if portfolio:
        target_user = portfolio.user
    else:
        target_user = get_object_or_404(CustomUser, corelink_id=identifier)
    
    # Get the specific project
    project = get_object_or_404(PortfolioProject, pk=pk, profile=target_user.portfolio)
    
    # Check if project has only PDF assets
    valid_assets = project.gallery.all()
    all_pdfs = False
    if valid_assets.exists():
        all_pdfs = all(asset.asset_type == 'DOCUMENT' for asset in valid_assets)
    
    context = {
        'profile': target_user.portfolio,
        'user': target_user,
        'project': project,
        'all_pdfs': all_pdfs,
    }
    
    return render(request, 'profiles/project_detail.html', context)


from django.shortcuts import render, get_object_or_404
from .models import Company


def company_public_profile(request, slug):
    """Renders the public company page at /p/company/<slug>/"""
    company = get_object_or_404(Company, slug=slug)
    team_members = company.members.filter(is_active=True).select_related('user')
    services = company.services.filter(is_active=True).order_by('order')

    # Grab ALL jobs directly via the related_name 'opportunities' from the JobPost model
    # We order them by newest first. Since there's no status filter, it grabs Drafts, Pending, Active, etc.
    job_list = company.opportunities.all().order_by('-created_at')

    context = {
        'company': company,
        'team_members': team_members,
        'services': services,
        'milestones': company.milestones.all().order_by('-year'),
        'news_list': company.news_articles.filter(is_published=True).order_by('-published_date'),

        # Add the job list to the context here so the HTML can see it!
        'job_list': job_list,
    }
    return render(request, 'profiles/public_company.html', context)


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║ CLUSTER 3: LOBBY & IDENTITY SETTINGS                                       ║
# ║ Human Context: Where users manage the overarching identity details that    ║
# ║ wrap around their Lego blocks. Avatars, covers, roles, and global intent.  ║
# ╚════════════════════════════════════════════════════════════════════════════╝

class ProfileSettingsView(OracleUpdateMixin, RoleAwareFormMixin, LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'dashboard/portfolio/settings.html'
    success_url = reverse_lazy('profile_settings')

    def get_object(self):
        portfolio, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return portfolio

    def form_valid(self, form):
        # 1. Save the form (This now saves UserProfile AND CustomUser fields safely)
        response = super().form_valid(form)

        # 2. Update the User Role (Kept exactly as you had it)
        new_role = self.request.POST.get('role')
        valid_roles = ['VISIONARY', 'EXPERT', 'FOUNDER']
        needs_company_setup = False

        if new_role in valid_roles:
            user = self.request.user
            user.role = new_role
            user.save(update_fields=['role'])

            if new_role == 'FOUNDER':
                has_company = CompanyMember.objects.filter(
                    user=user,
                    is_active=True
                ).exists()

                if not has_company:
                    needs_company_setup = True

        # 3. Handle Conditional Redirect
        if needs_company_setup:
            messages.info(self.request, "Almost done! To be a Founder, you need to register your startup first.")
            return redirect('company_create')

        messages.success(self.request, "Your professional identity has been updated!")
        return response


class IdentityMediaView(OracleUpdateMixin, LoginRequiredMixin, UpdateView):
    """Handles updating Avatars and Cover Images."""
    model = CustomUser
    form_class = IdentityMediaForm
    template_name = 'dashboard/shared/media_settings.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        user = form.save(commit=False)
        # FIX: Convert empty string "" to None (NULL) to prevent Postgres IntegrityError
        if not user.email:
            user.email = None
        user.save()

        messages.success(self.request, "Visual identity updated.")
        return redirect(self.success_url)


@login_required
@require_POST
def delete_media_asset(request, asset_type):
    """Direct deletion endpoint for universal media resources (Avatar/Cover)."""
    user = request.user
    if asset_type == 'avatar' and user.avatar:
        user.avatar.delete(save=False)
        user.avatar = None
    elif asset_type == 'cover' and user.cover_image:
        user.cover_image.delete(save=False)
        user.cover_image = None

    # FIX: Convert empty string "" to None (NULL) to prevent Postgres IntegrityError
    if not user.email:
        user.email = None

    user.save()
    messages.success(request, "Image removed successfully.")
    return redirect('dashboard')


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║ CLUSTER 4: PORTFOLIO "LEGO BLOCKS" CRUD                                    ║
# ║ Human Context: Standard verifiable blocks (Experience, Skills, Projects).  ║
# ║ Designed for fast, structured rendering on the final public profile.       ║
# ╚════════════════════════════════════════════════════════════════════════════╝

# --- HEADLINES ---
class HeadlineListView(PortfolioSecurityMixin, ListView):
    model = ProfileHeadline
    template_name = 'dashboard/portfolio/headline_list.html'

class HeadlineCreateView(RoleAwareFormMixin, PortfolioCreateMixin, PortfolioSecurityMixin, CreateView):
    model = ProfileHeadline
    form_class = ProfileHeadlineForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_headlines')

class HeadlineUpdateView(OracleUpdateMixin, RoleAwareFormMixin, PortfolioSecurityMixin, UpdateView):
    model = ProfileHeadline
    form_class = ProfileHeadlineForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_headlines')

class HeadlineDeleteView(PortfolioSecurityMixin, DeleteView):
    model = ProfileHeadline
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('manage_headlines')


# --- SKILLS ---
class SkillListView(PortfolioSecurityMixin, ListView):
    model = Skill
    template_name = 'dashboard/portfolio/skill_list.html'

class SkillCreateView(RoleAwareFormMixin, PortfolioCreateMixin, PortfolioSecurityMixin, CreateView):
    model = Skill
    form_class = SkillForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_skills')

class SkillUpdateView(OracleUpdateMixin, RoleAwareFormMixin, PortfolioSecurityMixin, UpdateView):
    model = Skill
    form_class = SkillForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_skills')

class SkillDeleteView(PortfolioSecurityMixin, DeleteView):
    model = Skill
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('manage_skills')


# --- CREDENTIALS ---
class CredentialListView(PortfolioSecurityMixin, ListView):
    model = Credential
    template_name = 'dashboard/portfolio/credential_list.html'

class CredentialCreateView(RoleAwareFormMixin, PortfolioCreateMixin, PortfolioSecurityMixin, CreateView):
    model = Credential
    form_class = CredentialForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_credentials')

class CredentialUpdateView(OracleUpdateMixin, RoleAwareFormMixin, PortfolioSecurityMixin, UpdateView):
    model = Credential
    form_class = CredentialForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_credentials')

class CredentialDeleteView(PortfolioSecurityMixin, DeleteView):
    model = Credential
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('manage_credentials')


# --- EXPERIENCE ---
class ExperienceListView(PortfolioSecurityMixin, ListView):
    model = WorkExperience
    template_name = 'dashboard/portfolio/experience_list.html'

class ExperienceCreateView(RoleAwareFormMixin, PortfolioCreateMixin, PortfolioSecurityMixin, CreateView):
    model = WorkExperience
    form_class = WorkExperienceForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_experiences')

class ExperienceUpdateView(OracleUpdateMixin, RoleAwareFormMixin, PortfolioSecurityMixin, UpdateView):
    model = WorkExperience
    form_class = WorkExperienceForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_experiences')

class ExperienceDeleteView(PortfolioSecurityMixin, DeleteView):
    model = WorkExperience
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('manage_experiences')

# --- PROJECTS (WITH GALLERY HANDLING) ---
@login_required
def project_creation_guide(request):
    """Display interactive project creation guide for all professions."""
    return render(request, 'dashboard/portfolio/project_creation_guide.html')

class ProjectListView(PortfolioSecurityMixin, ListView):
    model = PortfolioProject
    template_name = 'dashboard/portfolio/project_list.html'

class ProjectCreateView(RoleAwareFormMixin, PortfolioSecurityMixin, CreateView):
    model = PortfolioProject
    form_class = PortfolioProjectForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_projects')

    def form_valid(self, form):
        with transaction.atomic():
            # Get portfolio and attach to form
            portfolio, _ = UserProfile.objects.get_or_create(user=self.request.user)
            form.instance.profile = portfolio
            
            # Ensure category is set (default to OTHER if not detected)
            if not form.cleaned_data.get('category'):
                form.instance.category = 'OTHER'
            
            self.object = form.save()
            
            # Handle multiple file uploads for the gallery (images and PDFs)
            uploaded_count = 0
            for file in self.request.FILES.getlist('gallery_images'):
                try:
                    # Validate file size (10MB max)
                    if file.size > 10 * 1024 * 1024:
                        logger.warning(f"File {file.name} exceeded 10MB limit")
                        messages.warning(self.request, f"File '{file.name}' was skipped (exceeds 10MB limit).")
                        continue
                    
                    # Auto-detect file type
                    if file.name.lower().endswith('.pdf'):
                        ProjectGallery.objects.create(
                            project=self.object,
                            asset_type='DOCUMENT',
                            document_file=file
                        )
                    else:
                        ProjectGallery.objects.create(
                            project=self.object,
                            asset_type='IMAGE',
                            image=file
                        )
                    uploaded_count += 1
                except Exception as e:
                    logger.error(f"Error uploading file {file.name}: {str(e)}")
                    messages.warning(self.request, f"Error uploading '{file.name}': {str(e)}")
                    continue
        
        msg = f"Project created successfully!"
        if uploaded_count > 0:
            msg += f" {uploaded_count} file(s) added."
        messages.success(self.request, msg)
        return redirect(self.get_success_url())

class ProjectUpdateView(OracleUpdateMixin, RoleAwareFormMixin, PortfolioSecurityMixin, UpdateView):
    model = PortfolioProject
    form_class = PortfolioProjectForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_projects')

    def form_valid(self, form):
        with transaction.atomic():
            # Ensure category is set (default to OTHER if not detected)
            if not form.cleaned_data.get('category'):
                form.instance.category = 'OTHER'
            
            self.object = form.save()
            
            # Handle adding new gallery files (images and PDFs)
            uploaded_count = 0
            for file in self.request.FILES.getlist('gallery_images'):
                try:
                    # Validate file size (10MB max)
                    if file.size > 10 * 1024 * 1024:
                        logger.warning(f"File {file.name} exceeded 10MB limit")
                        messages.warning(self.request, f"File '{file.name}' was skipped (exceeds 10MB limit).")
                        continue
                    
                    if file.name.lower().endswith('.pdf'):
                        ProjectGallery.objects.create(
                            project=self.object,
                            asset_type='DOCUMENT',
                            document_file=file
                        )
                    else:
                        ProjectGallery.objects.create(
                            project=self.object,
                            asset_type='IMAGE',
                            image=file
                        )
                    uploaded_count += 1
                except Exception as e:
                    logger.error(f"Error uploading file {file.name}: {str(e)}")
                    messages.warning(self.request, f"Error uploading '{file.name}': {str(e)}")
                    continue
            
            # Handle deleting selected gallery images
            if delete_ids := self.request.POST.getlist('delete_images'):
                ProjectGallery.objects.filter(id__in=delete_ids, project=self.object).delete()

        msg = "Project updated successfully!"
        if uploaded_count > 0:
            msg += f" {uploaded_count} new file(s) added."
        messages.success(self.request, msg)
        return redirect(self.get_success_url())

class ProjectDeleteView(PortfolioSecurityMixin, DeleteView):
    model = PortfolioProject
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('manage_projects')


@login_required
@require_GET
def auto_detect_project_category(request):
    """
    AI-Auto-Detect endpoint for project category.
    Analyzes title, description, and role to suggest the most likely category.
    Returns JSON with detected category, confidence score, and top suggestions.
    """
    from profiles.services import detect_project_category

    title = request.GET.get('title', '')
    description = request.GET.get('description', '')
    role = request.GET.get('role', '')

    result = detect_project_category(title, description, role)

    return JsonResponse({
        'success': True,
        'category': result['category'],
        'confidence': result['confidence'],
        'suggestions': result['suggestions']
    })


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║ CLUSTER 5: CONTENT PUBLISHING ENGINE                                       ║
# ║ Human Context: Handing the various forms of user expression (Logs, Essays, ║
# ║ Vision Blocks) leveraging our unified ContentPost architecture.            ║
# ╚════════════════════════════════════════════════════════════════════════════╝

class ContentPostListView(PortfolioSecurityMixin, ListView):
    model = ContentPost
    template_name = 'dashboard/portfolio/content_list.html'

class ContentPostCreateView(ContentPostSuccessUrlMixin, RoleAwareFormMixin, PortfolioCreateMixin, PortfolioSecurityMixin, CreateView):
    model = ContentPost
    form_class = ContentPostForm
    template_name = 'dashboard/portfolio/generic_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        requested_type = self.request.GET.get('type', 'ESSAY')
        valid_types = [choice[0] for choice in ContentPost.PostType.choices]
        if requested_type not in valid_types:
            requested_type = 'ESSAY'
        kwargs['post_type'] = requested_type
        return kwargs

class ContentPostUpdateView(OracleUpdateMixin, ContentPostSuccessUrlMixin, RoleAwareFormMixin, PortfolioSecurityMixin, UpdateView):
    model = ContentPost
    form_class = ContentPostForm
    template_name = 'dashboard/portfolio/generic_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if getattr(self, 'object', None):
            kwargs['post_type'] = self.object.post_type
        return kwargs

class ContentPostDeleteView(ContentPostSuccessUrlMixin, PortfolioSecurityMixin, DeleteView):
    model = ContentPost
    template_name = 'dashboard/shared/confirm_delete.html'


class GrowthLogListView(PortfolioSecurityMixin, ListView):
    model = ContentPost
    template_name = 'dashboard/portfolio/growth_log_list.html'
    context_object_name = 'growth_logs'

    def get_queryset(self):
        return super().get_queryset().filter(post_type='GROWTH_LOG')

class EssayListView(PortfolioSecurityMixin, ListView):
    model = ContentPost
    template_name = 'dashboard/portfolio/essay_list.html'
    context_object_name = 'essays'

    def get_queryset(self):
        return super().get_queryset().filter(post_type='ESSAY')

class VisionBlockListView(PortfolioSecurityMixin, ListView):
    model = ContentPost
    template_name = 'dashboard/portfolio/vision_block_list.html'
    context_object_name = 'vision_blocks'

    def get_queryset(self):
        return super().get_queryset().filter(post_type='VISION_BLOCK')


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║ CLUSTER 6: FUTURE NETWORKING (Intent & Opportunities)                      ║
# ║ Human Context: Captures the user's career trajectory goals and ephemeral   ║
# ║ needs (e.g. "Looking for a co-founder this weekend").                      ║
# ╚════════════════════════════════════════════════════════════════════════════╝

# --- JOB PREFERENCES ---
class PreferenceListView(PortfolioSecurityMixin, ListView):
    model = UnifiedJobPreference
    template_name = 'dashboard/portfolio/preference_list.html'

class PreferenceCreateView(RoleAwareFormMixin, PortfolioCreateMixin, PortfolioSecurityMixin, CreateView):
    model = UnifiedJobPreference
    form_class = JobPreferenceForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_preferences')

class PreferenceUpdateView(OracleUpdateMixin, RoleAwareFormMixin, PortfolioSecurityMixin, UpdateView):
    model = UnifiedJobPreference
    form_class = JobPreferenceForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_preferences')

class PreferenceDeleteView(PortfolioSecurityMixin, DeleteView):
    model = UnifiedJobPreference
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('manage_preferences')


# --- LANGUAGES ---
class LanguageListView(PortfolioSecurityMixin, ListView):
    model = Language
    template_name = 'dashboard/portfolio/language_list.html'

class LanguageCreateView(RoleAwareFormMixin, PortfolioCreateMixin, PortfolioSecurityMixin, CreateView):
    model = Language
    form_class = LanguageForm
    template_name = 'dashboard/portfolio/language_form.html'
    success_url = reverse_lazy('language_list')

class LanguageUpdateView(OracleUpdateMixin, RoleAwareFormMixin, PortfolioSecurityMixin, UpdateView):
    model = Language
    form_class = LanguageForm
    template_name = 'dashboard/portfolio/language_form.html'
    success_url = reverse_lazy('language_list')

class LanguageDeleteView(PortfolioSecurityMixin, DeleteView):
    model = Language
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('language_list')


# --- LIVE OPPORTUNITIES (The 10x Feature) ---
class OpportunityListView(PortfolioSecurityMixin, ListView):
    model = LiveOpportunity
    template_name = 'dashboard/portfolio/opportunity_list.html'

class OpportunityCreateView(RoleAwareFormMixin, PortfolioCreateMixin, PortfolioSecurityMixin, CreateView):
    model = LiveOpportunity
    form_class = LiveOpportunityForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_opportunities')

class OpportunityUpdateView(OracleUpdateMixin, RoleAwareFormMixin, PortfolioSecurityMixin, UpdateView):
    model = LiveOpportunity
    form_class = LiveOpportunityForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_opportunities')

class OpportunityDeleteView(PortfolioSecurityMixin, DeleteView):
    model = LiveOpportunity
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('manage_opportunities')


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║ CLUSTER 7: THE "RIGHT NOW" SOCIAL ECOSYSTEM                                ║
# ║ Human Context: The living heartbeat of the platform. Handling the          ║
# ║ creation of active status updates and the high-speed AJAX engagement API.  ║
# ╚════════════════════════════════════════════════════════════════════════════╝

class RightNowListView(PortfolioSecurityMixin, ListView):
    model = RightNowPost
    template_name = 'dashboard/portfolio/right_now_list.html'
    context_object_name = 'right_now_posts'

class RightNowCreateView(RoleAwareFormMixin, PortfolioSecurityMixin, CreateView):
    model = RightNowPost
    form_class = RightNowPostForm
    template_name = 'dashboard/portfolio/right_now_form.html'
    success_url = reverse_lazy('manage_right_now')

    def form_valid(self, form):
        with transaction.atomic():
            # 1. Get or create the user's portfolio and attach it
            portfolio, _ = UserProfile.objects.get_or_create(user=self.request.user)
            form.instance.profile = portfolio

            # 2. Save the post (This triggers the metadata link scraping in the model)
            self.object = form.save()

            # 3. Handle multiple image uploads for the gallery
            for image in self.request.FILES.getlist('gallery_images'):
                RightNowMedia.objects.create(post=self.object, image=image)

        messages.success(self.request, "Right Now update published successfully.")
        return redirect(self.get_success_url())

class RightNowUpdateView(OracleUpdateMixin, RoleAwareFormMixin, PortfolioSecurityMixin, UpdateView):
    model = RightNowPost
    form_class = RightNowPostForm
    template_name = 'dashboard/portfolio/right_now_form.html'
    success_url = reverse_lazy('manage_right_now')

    def form_valid(self, form):
        with transaction.atomic():
            # 1. Save the post (Triggers metadata refresh if the link changed)
            self.object = form.save()

            # 2. Handle adding new gallery images
            for image in self.request.FILES.getlist('gallery_images'):
                RightNowMedia.objects.create(post=self.object, image=image)

            # 3. Handle deleting selected gallery images
            if delete_ids := self.request.POST.getlist('delete_images'):
                RightNowMedia.objects.filter(id__in=delete_ids, post=self.object).delete()

        messages.success(self.request, "Right Now update modified.")
        return redirect(self.get_success_url())


# ═══════════════════════════════════════════════════════════════════════════════
# INLINE "RIGHT NOW" CREATION API
# ═══════════════════════════════════════════════════════════════════════════════
@login_required
@require_POST
def api_create_right_now(request):
    """
    Handles the inline AJAX composer from the dashboard.
    Saves the post, attaches images, AND updates the user's primary profile intent.
    """
    body_narrative = request.POST.get('body_narrative', '').strip()
    current_search = request.POST.get('current_search', 'LEARNING')
    images = request.FILES.getlist('gallery_images')

    if not body_narrative:
        return JsonResponse({'success': False, 'error': 'Update cannot be empty'}, status=400)

    with transaction.atomic():
        # 1. Fetch the user's profile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        # 2. Sync Profile Intent: Whatever they select in the post becomes their main status
        if profile.current_search != current_search:
            profile.current_search = current_search
            # The model's save() method will automatically trigger `last_signal_update`
            profile.save(update_fields=['current_search'])

        # 3. Create the Post (Title is intentionally left null as requested)
        post = RightNowPost.objects.create(
            profile=profile,
            title=None,
            body_narrative=body_narrative,
            current_search=current_search,
            collaboration_status=profile.collaboration_status,
            is_published=True,
            is_active_focus=True  # Automatically pins this to the top of their profile
        )

        # 4. Attach Media
        for image in images:
            RightNowMedia.objects.create(post=post, image=image)

    return JsonResponse({
        'success': True,
        'post_id': post.id,
        'new_search': current_search
    })

class RightNowDeleteView(PortfolioSecurityMixin, DeleteView):
    model = RightNowPost
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('manage_right_now')


# --- PHASE 2: ENGAGEMENT API (Lightning Fast AJAX Endpoints) ---
@login_required
@require_POST
def api_toggle_like(request, post_id):
    """
    Toggles a like on or off.
    Returns the new count and boolean status.
    """
    post = get_object_or_404(RightNowPost, id=post_id)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Try to get the like. If it exists, user is Unliking. If it doesn't, user is Liking.
    like_qs = RightNowLike.objects.filter(post=post, profile=profile)

    if like_qs.exists():
        like_qs.delete()
        is_liked = False
    else:
        RightNowLike.objects.create(post=post, profile=profile)
        is_liked = True

    # Refresh the post from the database to get the exact count updated by our Signals!
    post.refresh_from_db()

    return JsonResponse({
        'status': 'success',
        'is_liked': is_liked,
        'likes_count': post.likes_count
    })

@login_required
@require_POST
def api_add_comment(request, post_id):
    """
    Accepts JSON payload with comment text and saves it.
    Returns the fresh comment data to be injected into the UI instantly.
    """
    post = get_object_or_404(RightNowPost, id=post_id)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    try:
        data = json.loads(request.body)
        body_text = data.get('body', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    if not body_text:
        return JsonResponse({'status': 'error', 'message': 'Comment cannot be empty'}, status=400)

    # Create the comment
    comment = RightNowComment.objects.create(
        post=post,
        author=profile,
        body=body_text
    )

    post.refresh_from_db()  # Get the new comment count

    # Return the newly created comment data so JS can build it on the screen
    avatar_url = profile.user.avatar.url if profile.user.avatar else None

    return JsonResponse({
        'status': 'success',
        'comments_count': post.comments_count,
        'comment': {
            'id': str(comment.id),
            'author_name': profile.user.full_name or "Unknown",
            'author_url': profile.user.get_absolute_url() if hasattr(profile.user, 'get_absolute_url') else '#',
            'author_avatar': avatar_url,
            'body': comment.body,
            'time_ago': "Just now"
        }
    })

@require_GET
def api_get_comments(request, post_id):
    """
    Fetches all comments for a specific post when the user clicks the comment button.
    """
    post = get_object_or_404(RightNowPost, id=post_id)
    comments = RightNowComment.objects.filter(post=post).select_related('author__user')

    comments_data = []
    for comment in comments:
        avatar_url = comment.author.user.avatar.url if comment.author.user.avatar else None

        comments_data.append({
            'id': str(comment.id),
            'author_name': comment.author.user.full_name or "Unknown",
            'author_url': comment.author.user.get_absolute_url() if hasattr(comment.author.user, 'get_absolute_url') else '#',
            'author_avatar': avatar_url,
            'body': comment.body,
            # Simple formatting for older comments
            'time_ago': comment.created_at.strftime("%b %d, %Y")
        })

    return JsonResponse({
        'status': 'success',
        'comments': comments_data
    })


@login_required
@require_GET
def api_get_oracle_score(request):
    """
    Returns the current user's Oracle score for real-time progress updates.
    """
    try:
        portfolio = request.user.portfolio
        return JsonResponse({
            'status': 'success',
            'oracle_score': portfolio.oracle_score or 0,
            'admin_rating': portfolio.admin_rating or 0
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'oracle_score': 0,
            'admin_rating': 0
        })


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║ CLUSTER 8: PERSONAL NETWORK & SOCIALS                                      ║
# ║ Human Context: Managing the user's external links and contact preferences. ║
# ╚════════════════════════════════════════════════════════════════════════════╝

class NetworkListView(LoginRequiredMixin, ListView):
    """Displays both Social Links and Contact Methods for the user."""
    template_name = 'dashboard/portfolio/network_list.html'
    context_object_name = 'socials'

    def get_queryset(self):
        return UniversalSocialLink.objects.filter(user=self.request.user).order_by('order')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['contacts'] = UniversalContactMethod.objects.filter(user=self.request.user).order_by('-created_at')
        return ctx

# --- SOCIAL LINKS ---
class SocialCreateView(LoginRequiredMixin, CreateView):
    model = UniversalSocialLink
    form_class = SocialLinkForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_network')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class SocialUpdateView(OracleUpdateMixin, LoginRequiredMixin, UpdateView):
    model = UniversalSocialLink
    form_class = SocialLinkForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_network')

    def get_queryset(self):
        return UniversalSocialLink.objects.filter(user=self.request.user)

class SocialDeleteView(LoginRequiredMixin, DeleteView):
    model = UniversalSocialLink
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('manage_network')

    def get_queryset(self):
        return UniversalSocialLink.objects.filter(user=self.request.user)

# --- CONTACT METHODS ---
class ContactCreateView(LoginRequiredMixin, CreateView):
    model = UniversalContactMethod
    form_class = ContactMethodForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_network')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class ContactUpdateView(OracleUpdateMixin, LoginRequiredMixin, UpdateView):
    model = UniversalContactMethod
    form_class = ContactMethodForm
    template_name = 'dashboard/portfolio/generic_form.html'
    success_url = reverse_lazy('manage_network')

    def get_queryset(self):
        return UniversalContactMethod.objects.filter(user=self.request.user)

class ContactDeleteView(LoginRequiredMixin, DeleteView):
    model = UniversalContactMethod
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('manage_network')

    def get_queryset(self):
        return UniversalContactMethod.objects.filter(user=self.request.user)


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║ CLUSTER 9: COMPANY SETUP & ADMINISTRATION                                  ║
# ║ Human Context: Specialized flow for Founders to initialize their startup,  ║
# ║ manage high-level settings, media assets, and their internal team.         ║
# ╚════════════════════════════════════════════════════════════════════════════╝

@login_required
def company_create(request):
    """Special onboarding page for users claiming the FOUNDER role."""
    if request.method == "POST":
        name = request.POST.get('name')
        sector = request.POST.get('sector')
        location = request.POST.get('location')
        mission_stmt = request.POST.get('mission_stmt', '')

        if name and sector:
            # 1. Create the Business Entity
            company = Company.objects.create(
                name=name, sector=sector, location=location, mission_stmt=mission_stmt
            )

            # 2. Make the user the OWNER
            CompanyMember.objects.create(
                company=company, user=request.user, role='OWNER', job_title='Founder / CEO', is_active=True
            )

            # 3. Update User Role
            if request.user.role != 'FOUNDER':
                request.user.role = 'FOUNDER'
                request.user.save(update_fields=['role'])

            messages.success(request, f"Welcome to the Founder's club! {company.name} has been created.")

            # 🚨 FIX: Redirect to the PRIVATE ADMIN DASHBOARD, not the public profile!
            return redirect('company_admin_dashboard', slug=company.slug)

        else:
            messages.error(request, "Company Name and Sector are required.")

    return render(request, 'profiles/company_create.html')


class CompanyDashboardView(CompanyContextMixin, DetailView):
    """Main administrative dashboard for managing a company."""
    model = Company
    template_name = 'dashboard/company/admin_dashboard.html'

    def get_object(self):
        return self.get_company()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_object()
        context['active_members'] = company.members.filter(is_active=True).select_related('user')
        return context


class CompanyEditView(OracleUpdateMixin, LoginRequiredMixin, UpdateView):
    """Class-based view for editing a company profile, perfectly matching urls.py."""
    model = Company
    form_class = CompanyProfileUpdateForm
    template_name = 'dashboard/company/generic_form.html'

    def get_object(self, queryset=None):
        company = get_object_or_404(Company, slug=self.kwargs['slug'])
        # Security Check: Ensure user is OWNER or ADMIN
        if not CompanyMember.objects.filter(company=company, user=self.request.user, is_active=True, role__in=['OWNER', 'ADMIN']).exists():
            raise PermissionDenied("You do not have administrative access to this company.")
        return company

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company'] = self.get_object()  # Pass company to template context
        return context

    def form_valid(self, form):
        messages.success(self.request, "Company profile updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('company_public_profile', kwargs={'slug': self.object.slug})


@login_required
@require_POST
def company_quick_update(request, slug):
    """AJAX endpoint for the Command Center & Mission Editor on the Company Dashboard."""
    try:
        # 1. Verify ownership
        company = get_object_or_404(Company, slug=slug)
        if not CompanyMember.objects.filter(company=company, user=request.user, role__in=['OWNER', 'ADMIN'],
                                            is_active=True).exists():
            return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)

        # 2. Parse JSON
        data = json.loads(request.body)

        # We will track which fields are actually being updated so we only save what we need
        fields_to_update = []

        # 3. Handle Command Center Updates
        if 'is_hiring' in data:
            company.is_hiring = bool(data.get('is_hiring', False))
            fields_to_update.append('is_hiring')

        if 'looking_for' in data:
            company.looking_for = data.get('looking_for', 'BUILDING')
            fields_to_update.append('looking_for')

        # 4. Handle Mission Statement Updates (from the new Pop-up modal)
        if 'mission_stmt' in data:
            company.mission_stmt = data.get('mission_stmt', '').strip()
            fields_to_update.append('mission_stmt')

        # 5. Save only the updated fields
        if fields_to_update:
            company.save(update_fields=fields_to_update)

        return JsonResponse({'status': 'success', 'message': 'Company updated'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


from django.views.generic import DetailView
from profiles.models import CompanyService

class ServiceDetailView(DetailView):
    """Public detail page for a specific company service/product."""
    model = CompanyService
    template_name = 'profiles/public_service_detail.html'
    context_object_name = 'service'

    def get_queryset(self):
        # Ensure we only show active services
        return CompanyService.objects.filter(is_active=True).select_related('company')
@login_required
def company_media_manage(request, slug):
    """AJAX and HTML compatible Company Media Manager."""
    company = get_object_or_404(Company, slug=slug, members__user=request.user)

    # Security: Ensure user is OWNER or ADMIN
    if not CompanyMember.objects.filter(company=company, user=request.user, is_active=True,
                                        role__in=['OWNER', 'ADMIN']).exists():
        raise PermissionDenied("You do not have permission to manage this company's media.")

    if request.method == 'POST':
        action = request.POST.get('action')

        # 1. Handle Standard HTML Form Deletions (Remove Buttons)
        if action == 'remove_logo' and company.logo:
            company.logo.delete(save=True)
            messages.success(request, "Company logo removed successfully.")
            return redirect('company_media_manage', slug=company.slug)

        elif action == 'remove_cover' and company.cover_image:
            company.cover_image.delete(save=True)
            messages.success(request, "Company banner removed successfully.")
            return redirect('company_media_manage', slug=company.slug)

        # 2. Handle CropperJS Uploads (AJAX)
        if 'logo' in request.FILES:
            company.logo = request.FILES['logo']
            company.save()
            return JsonResponse({'status': 'success', 'message': 'Logo updated.'})

        elif 'cover_image' in request.FILES:
            company.cover_image = request.FILES['cover_image']
            company.save()
            return JsonResponse({'status': 'success', 'message': 'Cover updated.'})

        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    return render(request, 'dashboard/company/media_manage.html', {'company': company})
@login_required
def company_team_manage(request, slug):
    """Handles adding new team members to the company."""
    company = get_object_or_404(Company, slug=slug)

    if not CompanyMember.objects.filter(company=company, user=request.user, is_active=True, role__in=['OWNER', 'ADMIN']).exists():
        raise PermissionDenied("Only Company Owners and Admins can manage the team.")

    if request.method == 'POST':
        form = AddCompanyMemberForm(request.POST)
        if form.is_valid():
            raw_id = form.cleaned_data['user_identifier'].strip().replace(" ", "")

            # Intelligent search covering ID variations and phone number formats
            search_variations = [raw_id]
            if raw_id.startswith('0'):
                search_variations.append(f"+251{raw_id[1:]}")
            elif raw_id.startswith('+251'):
                search_variations.append(f"0{raw_id[4:]}")

            target_user = CustomUser.objects.filter(Q(corelink_id=raw_id) | Q(phone_number__in=search_variations)).first()

            if target_user:
                CompanyMember.objects.update_or_create(
                    company=company, user=target_user,
                    defaults={'role': form.cleaned_data['role'], 'job_title': form.cleaned_data['job_title'], 'is_active': True}
                )
                messages.success(request, f"Team member updated successfully.")
            else:
                messages.error(request, "User not found. Please verify the ID or Phone Number.")
            return redirect('company_team_manage', slug=company.slug)

    return render(request, 'dashboard/company/team_manage.html', {
        'company': company,
        'form': AddCompanyMemberForm(),
        'team': company.members.filter(is_active=True).select_related('user').order_by('role')
    })


@login_required
@require_POST
def company_team_remove(request, slug, member_id):
    """Revokes active access for a team member and sets them to ALUMNI."""
    company = get_object_or_404(Company, slug=slug)

    if not CompanyMember.objects.filter(company=company, user=request.user, is_active=True, role__in=['OWNER', 'ADMIN']).exists():
        raise PermissionDenied("Only Company Owners and Admins can revoke access.")

    member = get_object_or_404(CompanyMember, id=member_id, company=company)

    if member.user == request.user:
        messages.error(request, "You cannot remove yourself.")
    else:
        member.is_active = False
        member.role = 'ALUMNI'
        member.save()
        messages.success(request, "Revoked team member access successfully.")

    return redirect('company_team_manage', slug=company.slug)


@login_required
@require_http_methods(["GET", "POST"])
def company_team_invite(request, slug):
    """Send invitation to join company team via profile URL, phone, or direct user."""
    import logging
    logger = logging.getLogger(__name__)
    
    company = get_object_or_404(Company, slug=slug)
    logger.info(f"company_team_invite called for company {slug} by user {request.user}")

    if not CompanyMember.objects.filter(company=company, user=request.user, is_active=True, role__in=['OWNER', 'ADMIN']).exists():
        logger.error(f"Permission denied for user {request.user} on company {company.name}")
        raise PermissionDenied("Only Company Owners and Admins can send invitations.")

    if request.method == 'POST':
        form = AddCompanyMemberForm(request.POST)
        is_valid = form.is_valid()
        logger.info(f"Form submitted. Valid: {is_valid}")
        if not is_valid:
            logger.error(f"Form errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return redirect('company_team_manage', slug=company.slug)
        if is_valid:
            raw_input = form.cleaned_data['user_identifier'].strip()
            role = form.cleaned_data['role']
            job_title = form.cleaned_data['job_title']

            target_user = None
            invitation_type = None
            identifier = None

            # Check if input is a profile URL
            if raw_input.startswith('http'):
                # Extract username from URL
                from urllib.parse import urlparse
                parsed = urlparse(raw_input)
                path_parts = parsed.path.strip('/').split('/')
                if len(path_parts) >= 2 and path_parts[0] == 'u':
                    username = path_parts[1]
                    target_user = CustomUser.objects.filter(username=username).first()
                    if target_user:
                        invitation_type = 'profile_url'
                        identifier = raw_input

            # If not found via URL, try phone search
            if not target_user:
                search_variations = [raw_input.replace(" ", "")]
                if raw_input.startswith('0'):
                    search_variations.append(f"+251{raw_input[1:]}")
                elif raw_input.startswith('+251'):
                    search_variations.append(f"0{raw_input[4:]}")

                target_user = CustomUser.objects.filter(
                    Q(corelink_id=raw_input) | Q(phone_number__in=search_variations) | Q(email__iexact=raw_input)
                ).first()

                if target_user:
                    invitation_type = 'phone'
                    identifier = raw_input

            # If user exists, create invitation
            if target_user:
                # Check if already a member
                is_member = CompanyMember.objects.filter(company=company, user=target_user, is_active=True).exists()
                if is_member:
                    messages.error(request, f"{target_user.full_name} is already a team member.")
                    return redirect('company_team_manage', slug=company.slug)

                # Check if pending invitation exists
                has_pending = CompanyInvitation.objects.filter(
                    company=company, invited_user=target_user, status=CompanyInvitation.Status.PENDING
                ).exists()
                if has_pending:
                    # Send a reminder notification about the existing invitation
                    from workspace.models import ChatMessage
                    # Get the pending invitation
                    pending_invitation = CompanyInvitation.objects.filter(
                        company=company, invited_user=target_user, status=CompanyInvitation.Status.PENDING
                    ).first()
                    try:
                        if pending_invitation:
                            chat_msg = ChatMessage.objects.create(
                                sender=request.user,
                                receiver=target_user,
                                body=f"[INVITATION:{pending_invitation.id}] Reminder: You have a pending invitation to join {company.name} as {job_title}."
                            )
                            logger.info(f"Created reminder ChatMessage {chat_msg.id} for existing invitation")
                        else:
                            chat_msg = ChatMessage.objects.create(
                                sender=request.user,
                                receiver=target_user,
                                body=f"Reminder: You have a pending invitation to join {company.name} as {job_title}."
                            )
                    except Exception as e:
                        logger.error(f"Failed to create reminder chat notification: {e}", exc_info=True)
                    
                    messages.warning(request, f"An invitation is already pending for {target_user.full_name}. A reminder has been sent to their inbox.")
                    return redirect('company_admin_dashboard', slug=company.slug)

                # Create invitation
                from django.utils import timezone
                from datetime import timedelta
                logger.info(f"Creating invitation for user {target_user} to company {company.name}")
                invitation = CompanyInvitation.objects.create(
                    company=company,
                    invited_user=target_user,
                    profile_url=identifier if invitation_type == 'profile_url' else None,
                    phone=identifier if invitation_type == 'phone' else None,
                    role=role,
                    job_title=job_title,
                    expires_at=timezone.now() + timedelta(days=7)
                )
                logger.info(f"CompanyInvitation created: {invitation.id}")
                
                # Create inbox notification for the invited user
                from workspace.models import ChatMessage
                logger.info(f"Attempting to create ChatMessage from {request.user} to {target_user}")
                try:
                    chat_msg = ChatMessage.objects.create(
                        sender=request.user,
                        receiver=target_user,
                        body=f"[INVITATION:{invitation.id}] You have been invited to join {company.name} as {job_title}."
                    )
                    logger.info(f"SUCCESS: Created ChatMessage {chat_msg.id} from {request.user} to {target_user} for company invitation")
                except Exception as e:
                    # Log error but don't fail the invitation
                    logger.error(f"FAILED to create chat notification for invitation: {e}", exc_info=True)
                
                messages.success(request, f"Invitation sent to {target_user.full_name}! They will receive a notification in their inbox.")
                logger.info(f"Redirecting to company_admin_dashboard for {company.slug}")
                return redirect('company_admin_dashboard', slug=company.slug)

            else:
                messages.error(request, "User not found. Please verify the profile URL, phone number, or email.")
                return redirect('company_team_manage', slug=company.slug)
        else:
            # Form validation failed
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return redirect('company_team_manage', slug=company.slug)

    return redirect('company_team_manage', slug=company.slug)


@login_required
@require_http_methods(["POST"])
def accept_company_invitation(request, invitation_id):
    """Accept a company invitation and add user as team member."""
    import logging
    logger = logging.getLogger(__name__)
    
    invitation = get_object_or_404(CompanyInvitation, id=invitation_id, invited_user=request.user)
    
    if invitation.status != CompanyInvitation.Status.PENDING:
        messages.error(request, "This invitation is no longer valid.")
        return redirect('chat_hub')
    
    if invitation.is_expired():
        invitation.status = CompanyInvitation.Status.EXPIRED
        invitation.save()
        messages.error(request, "This invitation has expired.")
        return redirect('chat_hub')
    
    # Add user as company member
    CompanyMember.objects.create(
        company=invitation.company,
        user=request.user,
        role=invitation.role,
        job_title=invitation.job_title,
        is_active=True
    )
    
    # Update invitation status
    invitation.status = CompanyInvitation.Status.ACCEPTED
    invitation.save()
    
    # Send confirmation message to the inviter
    from workspace.models import ChatMessage
    inviter = invitation.company.get_owner_or_admin()
    if inviter:
        try:
            ChatMessage.objects.create(
                sender=request.user,
                receiver=inviter,
                body=f"{request.user.full_name} has accepted the invitation to join {invitation.company.name} as {invitation.job_title}."
            )
        except Exception as e:
            logger.error(f"Failed to send acceptance notification: {e}")
    
    messages.success(request, f"You have successfully joined {invitation.company.name} as {invitation.job_title}!")
    return redirect('company_admin_dashboard', slug=invitation.company.slug)


@login_required
@require_http_methods(["POST"])
def decline_company_invitation(request, invitation_id):
    """Decline a company invitation."""
    import logging
    logger = logging.getLogger(__name__)
    
    invitation = get_object_or_404(CompanyInvitation, id=invitation_id, invited_user=request.user)
    
    if invitation.status != CompanyInvitation.Status.PENDING:
        messages.error(request, "This invitation is no longer valid.")
        return redirect('chat_hub')
    
    # Update invitation status
    invitation.status = CompanyInvitation.Status.DECLINED
    invitation.save()
    
    # Send notification to the inviter
    from workspace.models import ChatMessage
    inviter = invitation.company.get_owner_or_admin()
    if inviter:
        try:
            ChatMessage.objects.create(
                sender=request.user,
                receiver=inviter,
                body=f"{request.user.full_name} has declined the invitation to join {invitation.company.name}."
            )
        except Exception as e:
            logger.error(f"Failed to send decline notification: {e}")
    
    messages.info(request, f"You have declined the invitation to join {invitation.company.name}.")
    return redirect('chat_hub')


@login_required
@require_http_methods(["GET", "POST"])
def company_team_edit(request, slug, member_id):
    """Edit team member role and job title."""
    company = get_object_or_404(Company, slug=slug)

    if not CompanyMember.objects.filter(company=company, user=request.user, is_active=True, role__in=['OWNER', 'ADMIN']).exists():
        raise PermissionDenied("Only Company Owners and Admins can edit team members.")

    member = get_object_or_404(CompanyMember, id=member_id, company=company)

    if request.method == 'POST':
        member.role = request.POST.get('role')
        member.job_title = request.POST.get('job_title')
        member.save()
        messages.success(request, f"Team member updated successfully.")
        return redirect('company_team_manage', slug=company.slug)

    return render(request, 'dashboard/company/team_edit.html', {
        'company': company,
        'member': member,
        'role_choices': CompanyMember.Role.choices
    })


@login_required
def search_user_for_invitation(request):
    """API endpoint to search users by profile URL, phone, or email for invitation preview."""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'found': False})
    
    target_user = None
    
    # Check if input is a profile URL
    if query.startswith('http'):
        from urllib.parse import urlparse
        parsed = urlparse(query)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2 and path_parts[0] == 'u':
            username = path_parts[1]
            target_user = CustomUser.objects.filter(username=username).first()
    
    # If not found via URL, try phone search
    if not target_user:
        search_variations = [query.replace(" ", "")]
        if query.startswith('0'):
            search_variations.append(f"+251{query[1:]}")
        elif query.startswith('+251'):
            search_variations.append(f"0{query[4:]}")
        
        target_user = CustomUser.objects.filter(
            Q(corelink_id=query) | Q(phone_number__in=search_variations) | Q(email__iexact=query)
        ).first()
    
    if target_user:
        return JsonResponse({
            'found': True,
            'user': {
                'id': str(target_user.id),
                'full_name': target_user.full_name,
                'avatar_url': target_user.get_avatar_url,
                'email': target_user.email,
                'phone': target_user.phone_number,
            }
        })
    
    return JsonResponse({'found': False})


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║ CLUSTER 10: COMPANY CMS (Services, Milestones, News, Socials)              ║
# ║ Human Context: Managing the public-facing content blocks of the company.   ║
# ╚════════════════════════════════════════════════════════════════════════════╝

# --- SERVICES ---
class ServiceListView(CompanyContextMixin, ListView):
    model = CompanyService
    template_name = 'dashboard/company/service_list.html'
    context_object_name = 'services'

    def get_queryset(self):
        return CompanyService.objects.filter(company=self.get_company()).order_by('order')

class ServiceCreateView(CompanyContextMixin, CreateView):
    model = CompanyService
    form_class = CompanyServiceForm
    template_name = 'dashboard/company/generic_form.html'
    success_url = reverse_lazy('manage_services')

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.company = self.get_company()
            self.object = form.save()
            # Handle multiple gallery images
            for image in self.request.FILES.getlist('gallery_images'):
                ServiceGalleryImage.objects.create(service=self.object, image=image)
        messages.success(self.request, "Service added successfully!")
        return redirect(self.get_success_url())

class ServiceUpdateView(OracleUpdateMixin, CompanyContextMixin, UpdateView):
    model = CompanyService
    form_class = CompanyServiceForm
    template_name = 'dashboard/company/generic_form.html'
    success_url = reverse_lazy('manage_services')

    def get_queryset(self):
        return CompanyService.objects.filter(company=self.get_company())

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            # Handle adding new gallery images
            for image in self.request.FILES.getlist('gallery_images'):
                ServiceGalleryImage.objects.create(service=self.object, image=image)
            # Handle deleting selected gallery images
            if delete_ids := self.request.POST.getlist('delete_images'):
                ServiceGalleryImage.objects.filter(id__in=delete_ids, service=self.object).delete()
        messages.success(self.request, "Service updated successfully!")
        return redirect(self.get_success_url())

class ServiceDeleteView(CompanyContextMixin, DeleteView):
    model = CompanyService
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('manage_services')

    def get_queryset(self):
        return CompanyService.objects.filter(company=self.get_company())


# --- MILESTONES ---
class MilestoneListView(CompanyContextMixin, ListView):
    model = CompanyMilestone
    template_name = 'dashboard/company/milestone_list.html'
    context_object_name = 'milestones'

    def get_queryset(self):
        return CompanyMilestone.objects.filter(company=self.get_company()).order_by('-year')

class MilestoneCreateView(CompanyContextMixin, CreateView):
    model = CompanyMilestone
    form_class = CompanyMilestoneForm
    template_name = 'dashboard/company/generic_form.html'
    success_url = reverse_lazy('manage_milestones')

    def form_valid(self, form):
        form.instance.company = self.get_company()
        return super().form_valid(form)

class MilestoneUpdateView(OracleUpdateMixin, CompanyContextMixin, UpdateView):
    model = CompanyMilestone
    form_class = CompanyMilestoneForm
    template_name = 'dashboard/company/generic_form.html'
    success_url = reverse_lazy('manage_milestones')

    def get_queryset(self):
        return CompanyMilestone.objects.filter(company=self.get_company())

class MilestoneDeleteView(CompanyContextMixin, DeleteView):
    model = CompanyMilestone
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('manage_milestones')

    def get_queryset(self):
        return CompanyMilestone.objects.filter(company=self.get_company())


# --- NEWS ARTICLES ---
class NewsListView(CompanyContextMixin, ListView):
    model = CompanyNews
    template_name = 'dashboard/company/news_list.html'
    context_object_name = 'news_list'

    def get_queryset(self):
        return CompanyNews.objects.filter(company=self.get_company()).order_by('-published_date')

class NewsCreateView(CompanyContextMixin, CreateView):
    model = CompanyNews
    form_class = CompanyNewsForm
    template_name = 'dashboard/company/generic_form.html'
    success_url = reverse_lazy('manage_news_list')

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.company = self.get_company()
            if not form.instance.slug:
                form.instance.slug = f"{slugify(form.instance.title)}-{self.get_company().id.hex[:4]}"
            self.object = form.save()
            # Handle multiple gallery images
            for image in self.request.FILES.getlist('gallery_images'):
                NewsGalleryImage.objects.create(news=self.object, image=image)
        messages.success(self.request, "Article published successfully!")
        return redirect(self.get_success_url())

class NewsUpdateView(OracleUpdateMixin, CompanyContextMixin, UpdateView):
    model = CompanyNews
    form_class = CompanyNewsForm
    template_name = 'dashboard/company/generic_form.html'
    success_url = reverse_lazy('manage_news_list')

    def get_queryset(self):
        return CompanyNews.objects.filter(company=self.get_company())

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            # Handle adding new gallery images
            for image in self.request.FILES.getlist('gallery_images'):
                NewsGalleryImage.objects.create(news=self.object, image=image)
            # Handle deleting selected gallery images
            if delete_ids := self.request.POST.getlist('delete_images'):
                NewsGalleryImage.objects.filter(id__in=delete_ids, news=self.object).delete()
        messages.success(self.request, "Article updated successfully!")
        return redirect(self.get_success_url())

class NewsDeleteView(CompanyContextMixin, DeleteView):
    model = CompanyNews
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('manage_news_list')

    def get_queryset(self):
        return CompanyNews.objects.filter(company=self.get_company())

class NewsDetailView(DetailView):
    """
    Publicly accessible view for reading a specific Company News article.
    """
    model = CompanyNews
    template_name = 'profiles/public_news_detail.html'
    context_object_name = 'article'

    def get_queryset(self):
        # Ensure only published news articles can be viewed publicly
        return CompanyNews.objects.filter(is_published=True)


# --- COMPANY CONTACTS & SOCIALS ---
class ManageCompanyNetworkView(CompanyContextMixin, ListView):
    template_name = 'dashboard/company/network_list.html'
    context_object_name = 'socials'

    def get_queryset(self):
        return CompanySocialLink.objects.filter(company=self.get_company()).order_by('order')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['contacts'] = CompanyContactMethod.objects.filter(company=self.get_company()).order_by('-created_at')
        return ctx

class CompanyContactCreateView(CompanyContextMixin, CreateView):
    model = CompanyContactMethod
    form_class = CompanyContactMethodForm
    template_name = 'dashboard/company/generic_form.html'
    success_url = reverse_lazy('manage_company_network')

    def form_valid(self, form):
        form.instance.company = self.get_company()
        return super().form_valid(form)

class CompanyContactUpdateView(OracleUpdateMixin, CompanyContextMixin, UpdateView):
    model = CompanyContactMethod
    form_class = CompanyContactMethodForm
    template_name = 'dashboard/company/generic_form.html'
    success_url = reverse_lazy('manage_company_network')

class CompanySocialCreateView(CompanyContextMixin, CreateView):
    model = CompanySocialLink
    form_class = CompanySocialLinkForm
    template_name = 'dashboard/company/generic_form.html'
    success_url = reverse_lazy('manage_company_network')

    def form_valid(self, form):
        form.instance.company = self.get_company()
        return super().form_valid(form)

class CompanySocialUpdateView(OracleUpdateMixin, CompanyContextMixin, UpdateView):
    model = CompanySocialLink
    form_class = CompanySocialLinkForm
    template_name = 'dashboard/company/generic_form.html'
    success_url = reverse_lazy('manage_company_network')


import io
import os
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from PIL import Image, ImageDraw, ImageFont

from profiles.models.new_unified_profile import UserProfile

User = get_user_model()


def profile_og_image(request, identifier):
    """Generates a dynamic OpenGraph image with Cover AND Avatar."""

    portfolio = UserProfile.objects.filter(slug=identifier).first()
    if portfolio:
        target_user = portfolio.user
    else:
        target_user = get_object_or_404(User, corelink_id=identifier)
        portfolio = getattr(target_user, 'portfolio', None)

    # 1. Create a blank canvas
    base_img = Image.new("RGB", (1200, 630), "#F8FAFC")
    draw = ImageDraw.Draw(base_img)

    # 2. Draw the Cover Image
    if target_user.cover_image:
        try:
            cover = Image.open(target_user.cover_image.file)
            cover = cover.resize((1200, 380), Image.Resampling.LANCZOS)
            base_img.paste(cover, (0, 0))
        except Exception:
            draw.rectangle([(0, 0), (1200, 380)], fill="#040F23")
    else:
        draw.rectangle([(0, 0), (1200, 380)], fill="#040F23")

    # 3. Draw the Bottom White Card
    draw.rectangle([(0, 380), (1200, 630)], fill="#ffffff")
    draw.line([(0, 380), (1200, 380)], fill="#E2E8F0", width=4)

    # ==========================================
    # 4. DRAW THE CIRCULAR PROFILE PICTURE
    # ==========================================
    if target_user.avatar:
        try:
            avatar = Image.open(target_user.avatar.file).convert("RGBA")
            avatar = avatar.resize((240, 240), Image.Resampling.LANCZOS)

            mask = Image.new('L', (240, 240), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, 240, 240), fill=255)

            border_size = 260
            border_img = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
            border_draw = ImageDraw.Draw(border_img)
            border_draw.ellipse((0, 0, border_size, border_size), fill="#ffffff")

            base_img.paste(border_img, (70, 250), border_img)
            base_img.paste(avatar, (80, 260), mask)
        except Exception:
            pass
    else:
        border_size = 260
        border_img = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border_img)
        border_draw.ellipse((0, 0, border_size, border_size), fill="#ffffff")
        base_img.paste(border_img, (70, 250), border_img)

        inner_circle = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
        inner_draw = ImageDraw.Draw(inner_circle)
        inner_draw.ellipse((0, 0, 240, 240), fill="#E2E8F0")
        base_img.paste(inner_circle, (80, 260), inner_circle)

    # ==========================================
    # 5. BULLETPROOF HUGE FONT FINDER (LINUX SAFE)
    # ==========================================
    font_name_obj = None
    font_title_obj = None

    try:
        # Ask Django to find the exact path to the file in cPanel
        font_path = finders.find('fonts/Inter_18pt-Bold.ttf')

        # If finders fails, look directly in the cPanel static root
        if not font_path and hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
            backup_path = os.path.join(settings.STATIC_ROOT, 'fonts', 'Inter_18pt-Bold.ttf')
            if os.path.exists(backup_path):
                font_path = backup_path

        # If it found the path, make it HUGE
        if font_path:
            font_name_obj = ImageFont.truetype(font_path, 80)
            font_title_obj = ImageFont.truetype(font_path, 40)
        else:
            raise Exception("Font file missing from server")

    except Exception as e:
        logger.warning(f"Font failed to load: {e}")
        # Absolute worst-case scenario (Tiny text)
        font_name_obj = ImageFont.load_default()
        font_title_obj = ImageFont.load_default()

    # ==========================================
    # 6. GET THE TEXT
    # ==========================================
    display_name = getattr(target_user, 'full_name', target_user.username)

    headline_text = "CoreLink Professional"
    if portfolio:
        headlines = portfolio.headlines.all()
        if headlines:
            headline_text = " | ".join([h.title for h in headlines])
        elif target_user.role:
            headline_text = target_user.get_role_display()

    if len(headline_text) > 65:
        headline_text = headline_text[:62] + "..."

    # ==========================================
    # 7. PAINT THE HUGE TEXT
    # ==========================================
    draw.text((360, 420), display_name, fill="#0F172A", font=font_name_obj)
    draw.text((360, 520), headline_text, fill="#0A66C2", font=font_title_obj)

    # ==========================================
    # 8. EXPORT IMAGE
    # ==========================================
    buffer = io.BytesIO()
    base_img.save(buffer, format="JPEG", quality=95)
    return HttpResponse(buffer.getvalue(), content_type="image/jpeg")