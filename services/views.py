"""
Service Views - Professional services offered by users
"""

import logging
from collections import defaultdict
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views.decorators.http import require_safe
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q, F
from django.db.models.functions import Length, Cast
from django.db.models import FloatField

from accounts.models import CustomUser
from profiles.models.user_profile import UserProfile
from .models import Service, ServiceGallery, ServiceCategory, ServiceSubcategory, ServiceTag, ServiceType
from .forms import ServiceForm, ServiceGalleryForm

logger = logging.getLogger(__name__)


# Mixins for security and functionality
class RoleAwareFormMixin:
    """Injects the request.user into the form so it dynamically adapts to roles."""
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class PortfolioSecurityMixin(LoginRequiredMixin):
    """Locks queries so users can only ever view/edit/delete their own portfolio blocks."""
    def get_queryset(self):
        # Handle models that might not have a profile field
        if hasattr(self.model, 'profile'):
            return self.model.objects.filter(profile__user=self.request.user)
        # For models with direct user relationship
        elif hasattr(self.model, 'user'):
            return self.model.objects.filter(user=self.request.user)
        else:
            # For nested models (like ServiceGallery), filter through parent
            return self.model.objects.all()


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


# --- SERVICES (User Services - distinct from Company Services) ---
class ServiceListView(PortfolioSecurityMixin, ListView):
    model = Service
    template_name = 'services/service_list.html'
    context_object_name = 'services'

    def get_queryset(self):
        # Ensure user has a portfolio
        if not hasattr(self.request.user, 'portfolio'):
            return Service.objects.none()
        return Service.objects.filter(profile=self.request.user.portfolio)


class ServiceCreateView(RoleAwareFormMixin, PortfolioCreateMixin, PortfolioSecurityMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = 'dashboard/services/generic_form.html'
    success_url = reverse_lazy('services:manage_services')

    def get_queryset(self):
        # Override to avoid filtering on create
        return Service.objects.all()

    def form_valid(self, form):
        with transaction.atomic():
            # Get portfolio and attach to form
            portfolio, _ = UserProfile.objects.get_or_create(user=self.request.user)
            form.instance.profile = portfolio
            
            self.object = form.save()
            
            # Handle multiple image uploads for the gallery
            uploaded_count = 0
            for image in self.request.FILES.getlist('gallery_images'):
                try:
                    # Validate file size (10MB max)
                    if image.size > 10 * 1024 * 1024:
                        logger.warning(f"File {image.name} exceeded 10MB limit")
                        messages.warning(self.request, f"File '{image.name}' was skipped (exceeds 10MB limit).")
                        continue
                    
                    ServiceGallery.objects.create(
                        service=self.object,
                        image=image
                    )
                    uploaded_count += 1
                except Exception as e:
                    logger.error(f"Error uploading file {image.name}: {str(e)}")
                    messages.warning(self.request, f"Error uploading '{image.name}': {str(e)}")
                    continue
        
        msg = "Service created successfully!"
        if uploaded_count > 0:
            msg += f" {uploaded_count} image(s) added to gallery."
        messages.success(self.request, msg)
        return redirect(self.get_success_url())


class ServiceUpdateView(OracleUpdateMixin, RoleAwareFormMixin, PortfolioSecurityMixin, UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = 'dashboard/services/generic_form.html'
    success_url = reverse_lazy('services:manage_services')

    def get_queryset(self):
        # Ensure user has a portfolio
        if not hasattr(self.request.user, 'portfolio'):
            return Service.objects.none()
        return Service.objects.filter(profile=self.request.user.portfolio)

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            
            # Handle adding new gallery images
            uploaded_count = 0
            for image in self.request.FILES.getlist('gallery_images'):
                try:
                    # Validate file size (10MB max)
                    if image.size > 10 * 1024 * 1024:
                        logger.warning(f"File {image.name} exceeded 10MB limit")
                        messages.warning(self.request, f"File '{image.name}' was skipped (exceeds 10MB limit).")
                        continue
                    
                    ServiceGallery.objects.create(
                        service=self.object,
                        image=image
                    )
                    uploaded_count += 1
                except Exception as e:
                    logger.error(f"Error uploading file {image.name}: {str(e)}")
                    messages.warning(self.request, f"Error uploading '{image.name}': {str(e)}")
                    continue
            
            # Handle deleting selected gallery images
            if delete_ids := self.request.POST.getlist('delete_images'):
                ServiceGallery.objects.filter(id__in=delete_ids, service=self.object).delete()
        
        msg = "Service updated successfully!"
        if uploaded_count > 0:
            msg += f" {uploaded_count} image(s) added to gallery."
        messages.success(self.request, msg)
        return redirect(self.get_success_url())


class ServiceDeleteView(PortfolioSecurityMixin, DeleteView):
    model = Service
    template_name = 'dashboard/shared/confirm_delete.html'
    success_url = reverse_lazy('services:manage_services')

    def get_queryset(self):
        # Ensure user has a portfolio
        if not hasattr(self.request.user, 'portfolio'):
            return Service.objects.none()
        return Service.objects.filter(profile=self.request.user.portfolio)


class ServiceGalleryListView(PortfolioSecurityMixin, ListView):
    model = ServiceGallery
    template_name = 'services/service_gallery_list.html'
    context_object_name = 'gallery_images'

    def get_queryset(self):
        # Filter gallery images for a specific service
        service_id = self.kwargs.get('service_id')
        if service_id:
            return ServiceGallery.objects.filter(service_id=service_id, service__profile__user=self.request.user)
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service_id = self.kwargs.get('service_id')
        if service_id:
            context['service'] = get_object_or_404(Service, id=service_id, profile__user=self.request.user)
        return context


class ServiceGalleryCreateView(RoleAwareFormMixin, CreateView):
    model = ServiceGallery
    form_class = ServiceGalleryForm
    template_name = 'dashboard/portfolio/generic_form.html'

    def get_success_url(self):
        return reverse('services:manage_service_gallery', kwargs={'service_id': self.object.service.id})

    def form_valid(self, form):
        service_id = self.kwargs.get('service_id')
        service = get_object_or_404(Service, id=service_id, profile__user=self.request.user)
        form.instance.service = service
        messages.success(self.request, "Gallery image added successfully.")
        return super().form_valid(form)


class ServiceGalleryUpdateView(OracleUpdateMixin, RoleAwareFormMixin, UpdateView):
    model = ServiceGallery
    form_class = ServiceGalleryForm
    template_name = 'dashboard/portfolio/generic_form.html'

    def get_success_url(self):
        return reverse('services:manage_service_gallery', kwargs={'service_id': self.object.service.id})

    def get_queryset(self):
        return ServiceGallery.objects.filter(service__profile__user=self.request.user)


class ServiceGalleryDeleteView(DeleteView):
    model = ServiceGallery
    template_name = 'dashboard/shared/confirm_delete.html'

    def get_success_url(self):
        return reverse('services:manage_service_gallery', kwargs={'service_id': self.object.service.id})

    def get_queryset(self):
        return ServiceGallery.objects.filter(service__profile__user=self.request.user)


# Public Service Detail View
def service_detail_view(request, identifier, pk):
    """
    Public Service Detail View.
    Shows full service information including gallery and description.
    """
    # Get the user profile from identifier (slug or CoreLink ID)
    target_user = None
    portfolio = UserProfile.objects.filter(slug=identifier).first()
    
    if portfolio:
        target_user = portfolio.user
    else:
        target_user = get_object_or_404(CustomUser, corelink_id=identifier)
    
    # Get the specific service
    if not hasattr(target_user, 'portfolio') or not target_user.portfolio:
        raise Http404("User profile not found")
    service = get_object_or_404(Service, pk=pk, profile=target_user.portfolio)
    
    context = {
        'profile': target_user.portfolio,
        'user': target_user,
        'service': service,
    }
    
    return render(request, 'services/service_detail.html', context)


# ==============================================================================
# 💼 SERVICE FEED (Public Discovery)
# ==============================================================================
@require_safe
def service_feed(request):
    """
    Service Marketplace Feed: Browse professional services offered by users.
    Prioritizes services with gallery images and rich descriptions.
    Prevents consecutive listings from the same user.
    Supports filtering by category, subcategory, tags, and service type.
    """
    raw_query = request.GET.get('q', '')
    category_slug = request.GET.get('category')
    subcategory_slug = request.GET.get('subcategory')
    tag_slug = request.GET.get('tag')
    service_type_slug = request.GET.get('type')

    base_services = Service.objects.filter(
        is_active=True,
        profile__user__is_active=True,
        profile__user__is_public=True,
        profile__user__is_nexus_visible=True
    ).exclude(
        profile__user__role='ADMIN'
    ).select_related(
        'profile', 'profile__user', 'category', 'subcategory', 'service_type'
    ).prefetch_related(
        'gallery', 'profile__headlines', 'tags'
    ).annotate(
        gallery_count=Count('gallery'),
        description_length=Length('description')
    )

    # Apply filters
    if category_slug:
        base_services = base_services.filter(category__slug=category_slug, category__is_active=True)
    
    if subcategory_slug:
        base_services = base_services.filter(subcategory__slug=subcategory_slug, subcategory__is_active=True)
    
    if tag_slug:
        base_services = base_services.filter(tags__slug=tag_slug)
    
    if service_type_slug:
        base_services = base_services.filter(service_type__slug=service_type_slug, service_type__is_active=True)

    if raw_query:
        # Search across service title, description, and user profile info
        from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
        
        search_vector = (
            SearchVector('title', weight='A') +
            SearchVector('description', weight='A') +
            SearchVector('profile__user__full_name', weight='B') +
            SearchVector('profile__headlines__title', weight='C') +
            SearchVector('tags__name', weight='B')
        )

        search_query = SearchQuery(raw_query, search_type='websearch')

        results = base_services.annotate(
            search_rank=Cast(SearchRank(search_vector, search_query) * 1000.0, FloatField())
        ).filter(
            search_rank__gt=0.0
        ).order_by('-search_rank', '-gallery_count', '-description_length')
    else:
        # Default ordering: prioritize services with gallery images
        results = base_services.order_by('-gallery_count', '-description_length', 'order', 'title')

    results = results.distinct()

    # Interleave services to prevent consecutive listings from same user
    results_list = list(results)
    
    if results_list:
        # Group services by user ID
        user_services = defaultdict(list)
        for service in results_list:
            user_id = service.profile.user.id
            user_services[user_id].append(service)
        
        # Interleave: take one service from each user in rotation
        interleaved = []
        user_ids = list(user_services.keys())
        max_services = max(len(services) for services in user_services.values())
        
        for i in range(max_services):
            for user_id in user_ids:
                if i < len(user_services[user_id]):
                    interleaved.append(user_services[user_id][i])
        
        results_list = interleaved

    paginator = Paginator(results_list, 24)
    page_number = request.GET.get('page')
    try:
        services_page = paginator.get_page(page_number)
    except PageNotAnInteger:
        services_page = paginator.get_page(1)
    except EmptyPage:
        services_page = paginator.get_page(paginator.num_pages)

    unread_count = 0
    if request.user.is_authenticated:
        try:
            from chat.models import ChatMessage
            unread_count = ChatMessage.objects.filter(receiver=request.user, is_read=False).count()
        except ImportError:
            pass

    # Get filter context for sidebar
    categories = ServiceCategory.objects.filter(is_active=True).prefetch_related('subcategories').order_by('order', 'name')
    service_types = ServiceType.objects.filter(is_active=True).order_by('order', 'name')
    featured_tags = ServiceTag.objects.filter(is_featured=True).order_by('-usage_count', 'name')[:20]

    # Get current filter objects for display
    current_category = None
    current_subcategory = None
    current_tag = None
    current_service_type = None
    
    if category_slug:
        current_category = ServiceCategory.objects.filter(slug=category_slug, is_active=True).first()
    if subcategory_slug:
        current_subcategory = ServiceSubcategory.objects.filter(slug=subcategory_slug, is_active=True).first()
    if tag_slug:
        current_tag = ServiceTag.objects.filter(slug=tag_slug).first()
    if service_type_slug:
        current_service_type = ServiceType.objects.filter(slug=service_type_slug, is_active=True).first()

    return render(request, 'services/service_feed.html', {
        'services': services_page,
        'search_query': raw_query,
        'unread_msg_count': unread_count,
        'user': request.user if request.user.is_authenticated else None,
        'categories': categories,
        'service_types': service_types,
        'featured_tags': featured_tags,
        'current_category': current_category,
        'current_subcategory': current_subcategory,
        'current_tag': current_tag,
        'current_service_type': current_service_type,
    })


class FeedServiceDetailView(DetailView):
    """
    World-class service detail page for the feed.
    Different from the profile service detail - this is a dedicated feed experience.
    """
    model = Service
    template_name = 'services/feed_service_detail.html'
    context_object_name = 'service'
    pk_url_kwarg = 'service_id'

    def get_queryset(self):
        return Service.objects.filter(
            profile__user__is_active=True
        ).select_related(
            'profile', 'profile__user'
        ).prefetch_related(
            'gallery', 'profile__headlines', 'profile__skills'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.object
        
        # Get related services from the same provider
        related_services = Service.objects.filter(
            profile=service.profile,
            profile__user__is_active=True
        ).exclude(id=service.id)[:4]
        
        # Get unread message count
        unread_count = 0
        if self.request.user.is_authenticated:
            try:
                from chat.models import ChatMessage
                unread_count = ChatMessage.objects.filter(receiver=self.request.user, is_read=False).count()
            except ImportError:
                pass
        
        context.update({
            'related_services': related_services,
            'unread_msg_count': unread_count,
        })
        return context
