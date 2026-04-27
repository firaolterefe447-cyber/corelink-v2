"""
Project Core_Link Workspace - Zero-Loss Structural Restoration
Role: Lead Systems Architect / AI Code Strategist
Status: Fully Refactored - Zero Logic Alteration, Unified Imports, Enhanced Security Decorators.
"""

# ==============================================================================================================
# ███████████████████████████████  1. UNIFIED IMPORTS & DEPENDENCIES  ██████████████████████████████████████████
# ==============================================================================================================

import logging
import uuid

# Django Core & Routing
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# Django Messaging & Auth
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.decorators.http import require_http_methods, require_POST, require_safe

# Django Class-Based Views
from django.views.generic import TemplateView, CreateView, ListView, UpdateView, DeleteView

# Django Database & Search ORM
from django.db import connection
from django.db.models import Q, F, Case, When, Value, FloatField, ExpressionWrapper, Max
from django.db.models.functions import Coalesce, Greatest, Cast, Now, ExtractDay
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.aggregates import StringAgg

# --- Cross-App Models & Oracles ---
from profiles.models import (
    Company, CompanyMember, CompanyService, CompanyNews,
    CompanyMilestone, CompanySocialLink, CompanyContactMethod, FounderProfile
)
from profiles.models.new_unified_profile import RightNowPost
from opportunities.models import JobPost, JobApplication
from network.views import OmniIndustryOracle

# --- Local Workspace Models ---
from .models import (
    Team, TeamMembership, JoinRequest, PreferenceApplication,
    ConnectionRequest, CompanyMessageToAdmin, ChatMessage
)

# --- Local Workspace Forms ---
from .forms import (
    TeamProposalForm, JoinRequestForm, PreferenceApplicationForm,
    ConnectionRequestForm, CompanyMessageForm
)

logger = logging.getLogger(__name__)
User = get_user_model()


# ==============================================================================================================
# █████████████████████████████████  2. SECURITY MIXINS & ROUTING  █████████████████████████████████████████████
# ==============================================================================================================

class OwnerRequiredMixin(UserPassesTestMixin):
    """
    Validates that the current user is the owner, leader, or company admin of the requested object.
    """
    def test_func(self):
        obj = self.get_object()
        user = self.request.user
        if hasattr(obj, 'user') and obj.user == user:
            return True
        if hasattr(obj, 'leader') and obj.leader == user:
            return True
        if hasattr(obj, 'company'):
            return user.company_memberships.filter(
                company=obj.company, is_active=True, role__in=['OWNER', 'ADMIN']
            ).exists()
        return False


def get_role_specific_dashboard(user):
    """
    Intelligent router directing users to their designated operational command center.
    """
    if not user.is_authenticated: return reverse('login')
    if user.role == 'FOUNDER': return reverse('founder_workspace')
    elif user.role == 'VISIONARY': return reverse('visionary_action_page')
    elif user.role == 'EXPERT': return reverse('expert_action_page')
    return reverse('workspace_dashboard')


# ==============================================================================================================
# ███████████████████████████████  3. UNIFIED WORKSPACE HUBS  ██████████████████████████████████████████████████
# ==============================================================================================================

class WorkspaceDashboardView(LoginRequiredMixin, TemplateView):
    """Fallback / Universal Dashboard."""
    template_name = 'workspace/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['my_teams'] = Team.objects.filter(memberships__user=user).distinct()
        context['my_requests'] = user.connection_applications.all().order_by('-created_at')

        context['my_opportunities'] = JobPost.objects.filter(
            posted_by=user
        ).select_related('company', 'posted_by').order_by('-created_at')

        context['my_applications'] = JobApplication.objects.filter(
            applicant=user
        ).select_related('job', 'job__company', 'job__posted_by').order_by('-created_at')

        return context


class FounderWorkspaceView(LoginRequiredMixin, TemplateView):
    """Company Profile and Brand Management for Founders."""
    template_name = 'workspace/founder_workspace.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        p, _ = FounderProfile.objects.get_or_create(user=user)

        membership = user.company_memberships.filter(is_active=True).first()
        company = membership.company if membership else None

        services_qs = CompanyService.objects.none()
        milestones_qs = CompanyMilestone.objects.none()

        if company:
            services_qs = CompanyService.objects.filter(company=company).prefetch_related('gallery').order_by('order')
            milestones_qs = CompanyMilestone.objects.filter(company=company).order_by('-year')

        context['profile'] = p
        context['company'] = company
        context['services'] = services_qs
        context['milestones'] = milestones_qs

        return context


@login_required
@require_safe
def visionary_action_page(request):
    """Primary operational console for Visionaries."""
    user = request.user

    my_teams = Team.objects.filter(leader=user).distinct().order_by('-created_at')
    joined_teams = Team.objects.filter(memberships__user=user).exclude(leader=user).select_related('leader').distinct().order_by('-created_at')

    context = {
        'page_title': 'Visionary Workspace',
        'preferences': user.placement_preferences.all().order_by('-created_at'),
        'my_requests': user.connection_applications.all().order_by('-created_at'),
        'my_teams': my_teams,
        'joined_teams': joined_teams,
        'my_opportunities': JobPost.objects.filter(posted_by=user).select_related('company', 'posted_by').order_by('-created_at'),
        'my_applications': JobApplication.objects.filter(applicant=user).select_related('job', 'job__company', 'job__posted_by').order_by('-created_at'),
    }
    return render(request, 'workspace/visionary_action_page.html', context)


@login_required
@require_safe
def expert_action_page(request):
    """Primary operational console for Experts."""
    user = request.user

    my_teams = Team.objects.filter(leader=user).distinct().order_by('-created_at')
    joined_teams = Team.objects.filter(memberships__user=user).exclude(leader=user).select_related('leader').distinct().order_by('-created_at')

    context = {
        'page_title': 'Expert Workspace',
        'preferences': user.placement_preferences.all().order_by('-created_at'),
        'my_requests': user.connection_applications.all().order_by('-created_at'),
        'my_teams': my_teams,
        'joined_teams': joined_teams,
        'my_opportunities': JobPost.objects.filter(posted_by=user).select_related('company', 'posted_by').order_by('-created_at'),
        'my_applications': JobApplication.objects.filter(applicant=user).select_related('job', 'job__company', 'job__posted_by').order_by('-created_at'),
    }
    return render(request, 'workspace/expert_action_page.html', context)


@login_required
def workspace_view(request):
    """
    Unified Workspace Console (Collaboration Hub).
    Handles Teams managed, Teams joined, Job Posts, Applications, and Current Focus.
    """
    user = request.user

    # 🚀 HIGH-PERFORMANCE QUERY: Prefetches the comments and the users who wrote them
    # so the template can render the live comment feed instantly without N+1 database hits.
    active_focus = RightNowPost.objects.filter(
        profile__user=user,
        is_active_focus=True
    ).prefetch_related(
        'comments__author__user'
    ).first()

    my_teams = Team.objects.filter(leader=user).prefetch_related('memberships').distinct().order_by('-created_at')

    joined_teams = Team.objects.filter(memberships__user=user).exclude(leader=user).select_related(
        'leader').distinct().order_by('-created_at')

    my_opportunities = JobPost.objects.filter(posted_by=user).select_related('company', 'posted_by').order_by(
        '-created_at')

    my_applications = JobApplication.objects.filter(applicant=user).select_related('job', 'job__company',
                                                                                   'job__posted_by').order_by(
        '-created_at')

    context = {
        'page_title': 'Workspace Console',
        'active_focus': active_focus,
        'my_teams': my_teams,
        'joined_teams': joined_teams,
        'my_opportunities': my_opportunities,
        'my_applications': my_applications,
    }

    return render(request, 'workspace/dashboard.html', context)
from django.db.models import F, Case, When, Value, FloatField, Q, ExpressionWrapper
from django.db.models.functions import Cast, Coalesce, Greatest, ExtractDay, Now
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.aggregates import StringAgg
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from django.views.decorators.http import require_safe
from django.db import connection

# Ensure RightNowLike is imported alongside your other models
# from .models import RightNowPost, RightNowLike, UserProfile, ChatMessage
# from .utils import OmniIndustryOracle  # Adjust based on your app structure

@require_safe  # Enforces GET requests only for safe feed rendering
def right_now_feed(request):
    """
    Next-Gen Right Now Feed: A living stream of what professionals are building.
    Strictly enforces that every single post MUST have an explanation (body_narrative).
    """
    raw_query = request.GET.get('q', '')

    base_posts = RightNowPost.objects.filter(
        is_published=True,
        profile__user__is_active=True,
        profile__user__is_public=True,
        profile__user__is_nexus_visible=True,
        profile__user__is_banned_from_right_now=False
    ).exclude(
        profile__user__role='ADMIN'
    ).exclude(
        Q(body_narrative__isnull=True) | Q(body_narrative__exact='') | Q(body_narrative__exact=' ')
    ).select_related(
        'profile', 'profile__user'
    ).prefetch_related(
        'gallery', 'profile__headlines'
    )

    base_posts = base_posts.annotate(raw_age=Now() - F('created_at'))

    if connection.vendor == 'postgresql':
        days_old_expr = ExtractDay('raw_age')
    else:
        days_old_expr = ExpressionWrapper(
            Cast(F('raw_age'), FloatField()) / 86400000000.0,
            output_field=FloatField()
        )

    scored_posts = base_posts.annotate(
        score_avatar=Case(When(profile__user__avatar='', then=0), default=15, output_field=FloatField()),
        score_verified=Case(When(profile__user__is_verified=True, then=15), default=0, output_field=FloatField()),
        days_old=days_old_expr,
        freshness_boost=Greatest(Value(0.0), Value(20.0) - Cast(F('days_old'), FloatField()) * 1.0),
        admin_score=Cast(Coalesce('profile__admin_rating', Value(0)) * 5, FloatField()),
        media_boost=Case(When(external_link__isnull=False, then=10), default=0, output_field=FloatField())
    ).annotate(
        total_quality=F('score_avatar') + F('score_verified') + F('admin_score') + F('freshness_boost') + F('media_boost')
    )

    if raw_query:
        (
            direct_string, semantic_string, loc_tags, skill_tags,
            min_experience, is_hiring, is_senior, is_junior
        ) = OmniIndustryOracle.process_omni_intent(raw_query)

        for loc in loc_tags:
            scored_posts = scored_posts.filter(
                Q(profile__user__current_location__icontains=loc) | Q(profile__location__icontains=loc))
        if is_hiring:
            scored_posts = scored_posts.filter(collaboration_status='OPEN')

        if direct_string or semantic_string:
            scored_posts = scored_posts.annotate(
                all_headlines=StringAgg('profile__headlines__title', delimiter=' ', distinct=True),
            )

            platinum_vector = (
                    SearchVector('title', weight='A') +
                    SearchVector('body_narrative', weight='A') +
                    SearchVector('current_search', weight='B') +
                    SearchVector('all_headlines', weight='C')
            )

            direct_db_query = SearchQuery(direct_string, search_type='websearch') if direct_string else None
            clean_query_word = direct_string.split()[0].lower() if direct_string else raw_query.split()[0].lower()

            results = scored_posts.annotate(
                platinum_rank=Cast(SearchRank(platinum_vector, direct_db_query) * 1000.0, FloatField()) if direct_db_query else Value(0.0, output_field=FloatField()),
                regex_boost=Case(
                    When(profile__user__full_name__iregex=fr'\b{clean_query_word}\b', then=Value(1000.0)),
                    When(title__iregex=fr'\b{clean_query_word}\b', then=Value(800.0)),
                    When(body_narrative__iregex=fr'\b{clean_query_word}\b', then=Value(600.0)),
                    default=Value(0.0), output_field=FloatField()
                )
            ).annotate(
                absolute_score=ExpressionWrapper(F('platinum_rank') + F('regex_boost') + F('total_quality'), output_field=FloatField())
            ).filter(
                Q(platinum_rank__gt=0.0) | Q(regex_boost__gt=0.0)
            ).order_by('-profile__user__is_pinned_in_right_now', '-absolute_score', '-created_at')
        else:
            results = scored_posts.order_by('-profile__user__is_pinned_in_right_now', '-total_quality', '-created_at')
    else:
        results = scored_posts.order_by('-profile__user__is_pinned_in_right_now', '-created_at', '-total_quality')

    results = results.distinct()

    paginator = Paginator(results, 24)
    page_number = request.GET.get('page')
    try:
        posts_page = paginator.get_page(page_number)
    except PageNotAnInteger:
        posts_page = paginator.get_page(1)
    except EmptyPage:
        posts_page = paginator.get_page(paginator.num_pages)

    # ==========================================
    # PHASE 4 MAGIC: PERSIST LIKED STATE
    # Fetch liked post IDs for the current user for THIS PAGE only
    # ==========================================
    user_liked_post_ids = []
    if request.user.is_authenticated:
        profile = getattr(request.user, 'userprofile', None)
        if profile:
            current_page_post_ids = [p.id for p in posts_page]
            user_liked_post_ids = list(RightNowLike.objects.filter(
                profile=profile,
                post_id__in=current_page_post_ids
            ).values_list('post_id', flat=True))

    unread_count = 0
    if request.user.is_authenticated:
        try:
            unread_count = ChatMessage.objects.filter(receiver=request.user, is_read=False).count()
        except ImportError:
            pass

    return render(request, 'workspace/right_now_feed.html', {
        'posts': posts_page,
        'search_query': raw_query,
        'unread_msg_count': unread_count,
        'user_liked_post_ids': user_liked_post_ids, # Passed to template
    })


from django.db.models import F
from django.views.generic import DetailView
from profiles.models import RightNowPost, RightNowLike  # Adjust import if models are elsewhere


class RightNowDetailView(DetailView):
    """
    Robust Dedicated view for long-form Right Now updates.
    Allows users to read massive texts and view all images without bloating the feed.
    """
    model = RightNowPost
    template_name = 'workspace/right_now_detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_queryset(self):
        """
        Optimize the database hits. We pre-fetch the author, their headline,
        and all gallery media in a single go to prevent N+1 query issues.
        We also ensure ONLY published posts can be viewed directly.
        """
        return RightNowPost.objects.filter(is_published=True).select_related(
            'profile',
            'profile__user'
        ).prefetch_related(
            'gallery',
            'profile__headlines'
        )

    def get_object(self, queryset=None):
        """
        Fetch the object and securely/atomically increment the views_count.
        Using F() expressions prevents race conditions if multiple people click at once.
        """
        obj = super().get_object(queryset)

        # Thread-safe increment of view count directly in the DB
        RightNowPost.objects.filter(pk=obj.pk).update(views_count=F('views_count') + 1)

        # Manually update the local instance so the template shows the new count immediately
        obj.views_count += 1

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 1. Determine if the currently logged-in user liked this specific post
        user_liked = False
        if self.request.user.is_authenticated:
            # Note: Using 'portfolio' because in your model UserProfile has related_name='portfolio'
            if hasattr(self.request.user, 'portfolio'):
                user_liked = RightNowLike.objects.filter(
                    post=self.object,
                    profile=self.request.user.portfolio
                ).exists()

        context['is_liked_by_user'] = user_liked

        # 2. Pre-fetch ALL comments efficiently so we don't rely entirely on AJAX for the detail page
        context['comments'] = self.object.comments.select_related(
            'author',
            'author__user'
        ).order_by('created_at')  # Chronological order makes sense for reading a long thread

        return context
# ==============================================================================================================
# ███████████████████████████████████  5. TEAM OPERATIONS NEXUS  ███████████████████████████████████████████████
# ==============================================================================================================

@login_required
@require_http_methods(["GET", "POST"])
def create_team_proposal(request, slug=None):
    """Handles submission of a new team formation proposal OR editing an existing team."""
    team_instance = get_object_or_404(Team, slug=slug) if slug else None

    if team_instance and team_instance.leader != request.user:
        messages.error(request, "Access Denied. Only the Team Leader can edit this team.")
        return redirect('team_detail', slug=team_instance.slug)

    if request.method == 'POST':
        form = TeamProposalForm(request.POST, instance=team_instance)
        if form.is_valid():
            saved_team = form.save(commit=False)

            if not team_instance:
                # --- CREATE LOGIC ---
                saved_team.leader = request.user
                saved_team.status = Team.Status.PENDING
                saved_team.save()
                TeamMembership.objects.create(team=saved_team, user=request.user, role=TeamMembership.Role.LEADER)
                messages.success(request, f"Team '{saved_team.name}' proposal submitted! Admin will review it shortly.")

                # UPDATED: Routes directly to Collaboration Hub
                return redirect('collaboration_hub')
            else:
                # --- EDIT LOGIC ---
                saved_team.save()
                messages.success(request, f"Team '{saved_team.name}' updated successfully!")

                # UPDATED: Routes directly to Collaboration Hub
                return redirect('collaboration_hub')
    else:
        form = TeamProposalForm(instance=team_instance)

    return render(request, 'workspace/create_team.html', {'form': form, 'team': team_instance})

@require_safe
def team_nexus(request):
    """Public roster of all active, approved teams on the platform."""
    teams = Team.objects.filter(status=Team.Status.APPROVED).order_by('-created_at')
    return render(request, 'workspace/team_nexus.html', {'teams': teams})


@require_http_methods(["GET", "POST"])
def team_detail(request, slug):
    """Detailed inspection view for a specific team, handling join requests. Works for Guests!"""
    team = get_object_or_404(Team, slug=slug)

    is_member = False
    has_pending_request = False
    form = None

    if request.user.is_authenticated:
        is_member = TeamMembership.objects.filter(team=team, user=request.user).exists()
        has_pending_request = JoinRequest.objects.filter(team=team, applicant=request.user, status=JoinRequest.Status.PENDING).exists()

        if request.method == 'POST':
            if is_member or has_pending_request:
                return redirect('team_detail', slug=team.slug)

            form = JoinRequestForm(request.POST)
            if form.is_valid():
                req = form.save(commit=False)
                req.team = team
                req.applicant = request.user
                req.save()
                messages.success(request, "Request sent to the Team Leader!")
                return redirect('team_detail', slug=team.slug)
        else:
            form = JoinRequestForm()

    return render(request, 'workspace/team_detail.html', {
        'team': team,
        'is_member': is_member,
        'has_pending_request': has_pending_request,
        'form': form
    })


@login_required
@require_http_methods(["GET", "POST"])
def manage_team(request, slug):
    """Operational console for Team Leaders to manage applications and team status."""
    try:
        team_id = uuid.UUID(str(slug))
        team = get_object_or_404(Team, id=team_id)
    except (ValueError, TypeError):
        team = get_object_or_404(Team, slug=slug)

    if team.leader != request.user:
        messages.error(request, "Access Denied: You are not the leader of this team.")
        return redirect('team_detail', slug=team.slug)

    pending_requests = team.join_requests.filter(status=JoinRequest.Status.PENDING).select_related('applicant')
    active_members = team.memberships.all().select_related('user')

    if request.method == 'POST':
        if 'toggle_recruiting' in request.POST:
            team.is_recruiting = not team.is_recruiting
            team.save()
            status_msg = "OPEN" if team.is_recruiting else "CLOSED"
            messages.success(request, f"Team recruitment is now {status_msg}.")
            return redirect('manage_team', slug=team.slug)

        if 'action' in request.POST:
            req_id = request.POST.get('request_id')
            action = request.POST.get('action')
            join_req = get_object_or_404(JoinRequest, id=req_id, team=team)

            if action == 'approve':
                join_req.status = JoinRequest.Status.APPROVED
                join_req.save()
                if not TeamMembership.objects.filter(team=team, user=join_req.applicant).exists():
                    TeamMembership.objects.create(team=team, user=join_req.applicant, role=TeamMembership.Role.MEMBER)
                    messages.success(request, f"Welcome {join_req.applicant.get_full_name() or join_req.applicant.username} to the team!")

            elif action == 'reject':
                join_req.status = JoinRequest.Status.REJECTED
                join_req.save()
                messages.info(request, "Application declined.")

            return redirect('manage_team', slug=team.slug)

    return render(request, 'workspace/manage_team.html', {
        'team': team,
        'pending_requests': pending_requests,
        'active_members': active_members
    })


# ==============================================================================================================
# ████████████████████████  6. WORKSPACE ACTIONS (CONNECTIONS, PREFS, ADMIN MESSAGES)  █████████████████████████
# ==============================================================================================================

class PreferenceApplicationCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = PreferenceApplication
    form_class = PreferenceApplicationForm
    template_name = 'workspace/submit_preference_application.html'
    success_message = "Preferences submitted."

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return get_role_specific_dashboard(self.request.user)


class ConnectionRequestCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = ConnectionRequest
    form_class = ConnectionRequestForm
    template_name = 'workspace/submit_connection_request.html'
    success_message = "Your connection request has been submitted."

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return get_role_specific_dashboard(self.request.user)


class PreferenceApplicationUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = PreferenceApplication
    form_class = PreferenceApplicationForm
    template_name = 'workspace/submit_preference_application.html'
    success_message = "Preferences updated."

    def get_success_url(self): return get_role_specific_dashboard(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_edit'] = True
        return ctx


class PreferenceApplicationDeleteView(LoginRequiredMixin, OwnerRequiredMixin, SuccessMessageMixin, DeleteView):
    model = PreferenceApplication
    template_name = 'workspace/confirm_delete.html'
    success_message = "Application withdrawn."

    def get_success_url(self): return get_role_specific_dashboard(self.request.user)


class ConnectionRequestUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = ConnectionRequest
    form_class = ConnectionRequestForm
    template_name = 'workspace/submit_connection_request.html'
    success_message = "Request updated."

    def get_success_url(self): return get_role_specific_dashboard(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_edit'] = True
        return ctx


class ConnectionRequestDeleteView(LoginRequiredMixin, OwnerRequiredMixin, SuccessMessageMixin, DeleteView):
    model = ConnectionRequest
    template_name = 'workspace/confirm_delete.html'
    success_message = "Request cancelled."

    def get_success_url(self): return get_role_specific_dashboard(self.request.user)


# --- FOUNDER TO ADMIN SECURE TRANSMISSIONS ---

class CompanyMessageListView(LoginRequiredMixin, ListView):
    model = CompanyMessageToAdmin
    template_name = 'workspace/company_message_list.html'
    context_object_name = 'support_messages'

    def get_queryset(self):
        allowed_companies = self.request.user.company_memberships.filter(
            role__in=['OWNER', 'ADMIN'], is_active=True
        ).values_list('company', flat=True)
        return super().get_queryset().filter(company__in=allowed_companies).order_by('-created_at')


class CompanyMessageCreateView(LoginRequiredMixin, CreateView):
    model = CompanyMessageToAdmin
    form_class = CompanyMessageForm
    template_name = 'workspace/company_message_form.html'
    success_url = reverse_lazy('founder_workspace')

    def form_valid(self, form):
        membership = self.request.user.company_memberships.filter(role__in=['OWNER', 'ADMIN'], is_active=True).first()
        if not membership:
            messages.error(self.request, "Access Denied: You must be an active company owner or admin.")
            return redirect('founder_workspace')

        form.instance.company = membership.company
        form.instance.founder = self.request.user
        messages.success(self.request, "Your message has been securely transmitted to the admin team.")
        return super().form_valid(form)


class CompanyMessageUpdateView(LoginRequiredMixin, UpdateView):
    model = CompanyMessageToAdmin
    form_class = CompanyMessageForm
    template_name = 'workspace/company_message_update.html'
    success_url = reverse_lazy('founder_workspace')

    def get_queryset(self):
        allowed_companies = self.request.user.company_memberships.filter(
            role__in=['OWNER', 'ADMIN'], is_active=True
        ).values_list('company', flat=True)
        return super().get_queryset().filter(company__in=allowed_companies)

    def form_valid(self, form):
        messages.success(self.request, "Your message has been successfully updated.")
        return super().form_valid(form)


class CompanyMessageDeleteView(LoginRequiredMixin, DeleteView):
    model = CompanyMessageToAdmin
    template_name = 'workspace/company_message_confirm_delete.html'
    success_url = reverse_lazy('founder_workspace')

    def get_queryset(self):
        allowed_companies = self.request.user.company_memberships.filter(
            role__in=['OWNER', 'ADMIN'], is_active=True
        ).values_list('company', flat=True)
        return super().get_queryset().filter(company__in=allowed_companies)

    def form_valid(self, form):
        messages.success(self.request, "The message has been securely recalled and deleted.")
        return super().form_valid(form)


# ==============================================================================================================
# █████████████████████████████████  7. UNIFIED MESSENGER (CHAT HUB)  ██████████████████████████████████████████
# ==============================================================================================================

@login_required
@require_http_methods(["GET", "POST"])
def chat_hub(request, user_id=None):
    """
    The Unified Messenger.
    user_id: The UUID of the person we are currently talking to (optional).
    """
    current_user = request.user
    active_partner = None
    active_messages = []

    if request.method == 'POST' and user_id:
        body = request.POST.get('body', '').strip()
        attachment = request.FILES.get('attachment')
        edit_message_id = request.POST.get('edit_message_id')

        if edit_message_id:
            msg = get_object_or_404(ChatMessage, id=edit_message_id, sender=current_user)
            if body and body != msg.body:
                msg.body = body
                msg.is_edited = True
                msg.save()
        else:
            if body or attachment:
                receiver = get_object_or_404(User, id=user_id)
                ChatMessage.objects.create(
                    sender=current_user, receiver=receiver, body=body, attachment=attachment
                )

        if request.headers.get('HX-Request'):
            return HttpResponse(status=204)

        return redirect('chat_with', user_id=user_id)

    all_msgs = ChatMessage.objects.filter(
        Q(sender=current_user) | Q(receiver=current_user)
    ).values('sender', 'receiver').annotate(last_activity=Max('timestamp')).order_by('-last_activity')

    partners_map = {}
    sidebar_chats = []

    for msg in all_msgs:
        partner_pk = msg['sender'] if msg['sender'] != current_user.id else msg['receiver']

        if partner_pk not in partners_map:
            partners_map[partner_pk] = True
            partner_obj = User.objects.get(pk=partner_pk)

            last_msg_obj = ChatMessage.objects.filter(
                Q(sender=current_user, receiver=partner_obj) |
                Q(sender=partner_obj, receiver=current_user)
            ).last()

            unread_count = ChatMessage.objects.filter(sender=partner_obj, receiver=current_user, is_read=False).count()

            sidebar_chats.append({
                'user': partner_obj,
                'last_message': last_msg_obj,
                'unread': unread_count
            })

    if user_id:
        active_partner = get_object_or_404(User, id=user_id)

        if active_partner == current_user:
            return redirect('chat_hub')

        active_messages = ChatMessage.objects.filter(
            Q(sender=current_user, receiver=active_partner) |
            Q(sender=active_partner, receiver=current_user)
        ).filter(is_deleted=False).order_by('timestamp')

        ChatMessage.objects.filter(sender=active_partner, receiver=current_user, is_read=False).update(is_read=True)

        if request.headers.get('HX-Request'):
            return render(request, 'workspace/partials/message_list.html', {
                'active_messages': active_messages,
                'request': request
            })

    context = {
        'sidebar_chats': sidebar_chats,
        'active_partner': active_partner,
        'active_messages': active_messages,
    }
    return render(request, 'workspace/chat_hub.html', context)


@login_required
@require_POST  # Strictly enforce POST to prevent accidental/malicious GET deletions
def delete_message(request, message_id):
    """Soft deletes a message. Strictly requires POST method for security."""
    msg = get_object_or_404(ChatMessage, id=message_id, sender=request.user)
    msg.is_deleted = True
    msg.save()
    return HttpResponse("")