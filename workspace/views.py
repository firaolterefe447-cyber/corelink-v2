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
from django.db.models import Q, F, Case, When, Value, FloatField, ExpressionWrapper, Max, Count
from django.db.models.functions import Coalesce, Greatest, Cast, Now, ExtractDay, Length
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.aggregates import StringAgg

# --- Cross-App Models & Oracles ---
from profiles.models import (
    Company, CompanyMember, CompanyService, CompanyNews,
    CompanyMilestone, CompanySocialLink, CompanyContactMethod, FounderProfile
)
from profiles.models.new_unified_profile import RightNowPost
from opportunities.models import JobPost, JobApplication

# --- Local Workspace Models ---
from .models import (
    CompanyMessageToAdmin, ChatMessage
)

# --- Local Workspace Forms ---
from .forms import (
    CompanyMessageForm
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
    return reverse('right_now_feed')


# ==============================================================================================================
# ███████████████████████████████  3. UNIFIED WORKSPACE HUBS  ██████████████████████████████████████████████████
# ==============================================================================================================

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
        is_admin_selected=True,
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
    ).annotate(
        gallery_count=Count('gallery'),
        char_length=Length('body_narrative')
    )

    base_posts = base_posts.annotate(raw_age=Now() - F('created_at'))

    if connection.vendor == 'postgresql':
        days_old_expr = ExtractDay('raw_age')
    else:
        days_old_expr = ExpressionWrapper(
            Cast(F('raw_age'), FloatField()) / 86400000000.0,
            output_field=FloatField()
        )

    scored_posts = base_posts

    if raw_query:
        # Simple search without OmniIndustryOracle (network app removed)
        scored_posts = scored_posts.annotate(
            all_headlines=StringAgg('profile__headlines__title', delimiter=' ', distinct=True),
        )

        platinum_vector = (
                SearchVector('title', weight='A') +
                SearchVector('body_narrative', weight='A') +
                SearchVector('current_search', weight='B') +
                SearchVector('all_headlines', weight='C')
        )

        direct_db_query = SearchQuery(raw_query, search_type='websearch')
        clean_query_word = raw_query.split()[0].lower()

        results = scored_posts.annotate(
            platinum_rank=Cast(SearchRank(platinum_vector, direct_db_query) * 1000.0, FloatField()),
            regex_boost=Case(
                When(profile__user__full_name__iregex=fr'\b{clean_query_word}\b', then=Value(1000.0)),
                When(title__iregex=fr'\b{clean_query_word}\b', then=Value(800.0)),
                When(body_narrative__iregex=fr'\b{clean_query_word}\b', then=Value(600.0)),
                default=Value(0.0), output_field=FloatField()
            )
        ).annotate(
            absolute_score=ExpressionWrapper(F('platinum_rank') + F('regex_boost'), output_field=FloatField())
        ).filter(
            Q(platinum_rank__gt=0.0) | Q(regex_boost__gt=0.0)
        ).order_by('-profile__user__is_pinned_in_right_now', '-gallery_count', '-char_length')
    else:
        results = scored_posts.order_by('-profile__user__is_pinned_in_right_now', '-gallery_count', '-char_length')

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
# ███████████████████████████████████  8. ADMIN CURATION SYSTEM  ███████████████████████████████████████████████
# ==============================================================================================================

@login_required
@require_http_methods(["GET", "POST"])
def admin_curation_view(request):
    """
    Admin-only interface to curate which Right Now posts appear in the feed.
    Only admin-selected posts will be displayed to users.
    Posts are prioritized by gallery count and character length.
    """
    # Check if user is admin
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied: Admin only.")
        return redirect('dashboard')

    if request.method == 'POST':
        post_id = request.POST.get('post_id')
        action = request.POST.get('action')  # 'select' or 'deselect'

        if post_id:
            try:
                post = RightNowPost.objects.get(id=post_id)
                if action == 'select':
                    post.is_admin_selected = True
                    post.save()
                    messages.success(request, f"Post selected for feed.")
                elif action == 'deselect':
                    post.is_admin_selected = False
                    post.save()
                    messages.success(request, f"Post removed from feed.")
            except RightNowPost.DoesNotExist:
                messages.error(request, "Post not found.")

        return redirect('admin_curation')

    # GET request - show all posts with curation status
    posts = RightNowPost.objects.filter(
        is_published=True,
        profile__user__is_active=True
    ).select_related(
        'profile', 'profile__user'
    ).prefetch_related(
        'gallery', 'profile__headlines'
    ).annotate(
        gallery_count=Count('gallery'),
        char_length=Length('body_narrative')
    ).order_by('-created_at', '-is_admin_selected', '-gallery_count', '-char_length')

    # Stats
    total_posts = posts.count()
    selected_posts = posts.filter(is_admin_selected=True).count()
    not_selected_posts = total_posts - selected_posts

    context = {
        'posts': posts,
        'total_posts': total_posts,
        'selected_posts': selected_posts,
        'not_selected_posts': not_selected_posts,
    }

    return render(request, 'workspace/admin_curation.html', context)
# ==============================================================================================================
# ███████████████████████████████████  5. FOUNDER TO ADMIN SECURE TRANSMISSIONS  ███████████████████████████████████████████████
# ==============================================================================================================

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
    from django.http import JsonResponse
    return JsonResponse({'success': True, 'message_id': str(message_id)})