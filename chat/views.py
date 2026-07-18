"""
Project Core_Link Chat - Zero-Loss Structural Restoration
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
from opportunities.models import JobPost, JobApplication

# --- Local Chat Models ---
from .models import (
    CompanyMessageToAdmin, ChatMessage
)

# --- Local Chat Forms ---
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
# ███████████████████████████████████  5. FOUNDER TO ADMIN SECURE TRANSMISSIONS  ███████████████████████████████████████████████
# ==============================================================================================================

class CompanyMessageListView(LoginRequiredMixin, ListView):
    model = CompanyMessageToAdmin
    template_name = 'chat/company_message_list.html'
    context_object_name = 'support_messages'

    def get_queryset(self):
        allowed_companies = self.request.user.company_memberships.filter(
            role__in=['OWNER', 'ADMIN'], is_active=True
        ).values_list('company', flat=True)
        return super().get_queryset().filter(company__in=allowed_companies).order_by('-created_at')


class CompanyMessageCreateView(LoginRequiredMixin, CreateView):
    model = CompanyMessageToAdmin
    form_class = CompanyMessageForm
    template_name = 'chat/company_message_form.html'
    success_url = reverse_lazy('company_message_list')

    def form_valid(self, form):
        membership = self.request.user.company_memberships.filter(role__in=['OWNER', 'ADMIN'], is_active=True).first()
        if not membership:
            messages.error(self.request, "Access Denied: You must be an active company owner or admin.")
            return redirect('company_message_list')

        form.instance.company = membership.company
        form.instance.founder = self.request.user
        messages.success(self.request, "Your message has been securely transmitted to the admin team.")
        return super().form_valid(form)


class CompanyMessageUpdateView(LoginRequiredMixin, UpdateView):
    model = CompanyMessageToAdmin
    form_class = CompanyMessageForm
    template_name = 'chat/company_message_update.html'
    success_url = reverse_lazy('company_message_list')

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
    template_name = 'chat/company_message_confirm_delete.html'
    success_url = reverse_lazy('company_message_list')

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
            return render(request, 'chat/partials/message_list.html', {
                'active_messages': active_messages,
                'request': request
            })

    context = {
        'sidebar_chats': sidebar_chats,
        'active_partner': active_partner,
        'active_messages': active_messages,
    }
    return render(request, 'chat/chat_hub.html', context)


@login_required
@require_POST  # Strictly enforce POST to prevent accidental/malicious GET deletions
def delete_message(request, message_id):
    """Soft deletes a message. Strictly requires POST method for security."""
    msg = get_object_or_404(ChatMessage, id=message_id, sender=request.user)
    msg.is_deleted = True
    msg.save()
    from django.http import JsonResponse
    return JsonResponse({'success': True, 'message_id': str(message_id)})