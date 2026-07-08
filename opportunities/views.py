# opportunities/views.py
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView, DetailView, UpdateView, DeleteView
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.utils import timezone
from datetime import timedelta
from watson import search as watson
import re
import operator
from functools import reduce
from datetime import timedelta
import io
import os
from PIL import Image, ImageDraw, ImageFont
from django.contrib.staticfiles import finders
from django.conf import settings
from django.http import HttpResponse

from django.utils import timezone
from django.db.models import Q, Case, When, IntegerField, F, Value, Count
from django.views.generic import ListView

from .models import JobPost, Skill
from .forms import OpportunitySearchForm

from .models import JobPost, JobApplication
from .forms import OpportunitySubmissionForm, OpportunitySearchForm

# Assuming Project is in profiles.models based on your Challenge logic
from profiles.models import Company, CompanyMember, Project


# ==============================================================================
# HELPER: DRY PERMISSION CHECKER
# ==============================================================================
def can_manage_job(user, job):
    """Unified security check to prevent repeated code across recruiter views."""
    is_admin = getattr(user, 'role', None) == 'ADMIN' or user.is_staff
    if is_admin or job.posted_by == user:
        return True
    if job.company:
        return CompanyMember.objects.filter(
            user=user, company=job.company, role__in=['OWNER', 'ADMIN'], is_active=True
        ).exists()
    return False


# ==============================================================================
# 1. CREATION & MANAGEMENT (THE WORKSPACE)
# ==============================================================================

class OpportunityCreateView(LoginRequiredMixin, CreateView):
    model = JobPost
    form_class = OpportunitySubmissionForm
    template_name = 'opportunities/company/create_opportunity.html'
    success_url = reverse_lazy('opportunities:workspace_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            opportunity = form.save(commit=False)
            opportunity.posted_by = self.request.user
            is_admin = getattr(self.request.user, 'role', None) == 'ADMIN' or self.request.user.is_staff

            post_as = form.cleaned_data.get('post_as')

            if post_as == 'USER':
                opportunity.company = None
                opportunity.is_official_admin_post = False
            elif post_as == 'OFFICIAL_ADMIN':
                opportunity.company = None
                opportunity.is_official_admin_post = True
                opportunity.status = JobPost.Status.ACTIVE
            elif post_as.startswith('COMPANY_'):
                company_id = post_as.split('_')[1]
                company = Company.objects.filter(id=company_id).first()
                if company:
                    opportunity.company = company
                else:
                    form.add_error('post_as', "Invalid company selection.")
                    return self.form_invalid(form)

            if opportunity.external_url:
                opportunity.is_external = True

            # Force pending for non-admins to prevent spam
            if not is_admin:
                opportunity.status = JobPost.Status.PENDING

            opportunity.save()
            form.save_m2m()

        messages.success(self.request, "🚀 Opportunity submitted successfully!")
        return super().form_valid(form)


class WorkspaceOpportunityListView(LoginRequiredMixin, ListView):
    model = JobPost
    template_name = 'opportunities/company/my_opportunities.html'
    context_object_name = 'my_opportunities'

    def get_queryset(self):
        # Sort by most recent changes in the workspace
        return JobPost.objects.filter(posted_by=self.request.user).select_related('company').order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        context['total_jobs'] = queryset.count()
        context['active_jobs'] = queryset.filter(status='ACTIVE').count()
        context['pending_jobs'] = queryset.filter(status='PENDING').count()
        context['my_applications'] = JobApplication.objects.filter(
            applicant=self.request.user
        ).select_related('job').order_by('-created_at')
        return context


class OpportunityUpdateView(LoginRequiredMixin, UpdateView):
    model = JobPost
    form_class = OpportunitySubmissionForm
    template_name = 'opportunities/company/create_opportunity.html'
    success_url = reverse_lazy('opportunities:workspace_list')
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        is_admin = getattr(self.request.user, 'role', None) == 'ADMIN' or self.request.user.is_staff
        if is_admin:
            return JobPost.objects.all()
        return JobPost.objects.filter(posted_by=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit_mode'] = True
        return context


class OpportunityDeleteView(LoginRequiredMixin, DeleteView):
    model = JobPost
    template_name = 'opportunities/company/opportunity_confirm_delete.html'
    success_url = reverse_lazy('opportunities:workspace_list')
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        is_admin = getattr(self.request.user, 'role', None) == 'ADMIN' or self.request.user.is_staff
        if is_admin:
            return JobPost.objects.all()
        return JobPost.objects.filter(posted_by=self.request.user)


# ==============================================================================
# 2. PUBLIC FEED & DISCOVERY
# ==============================================================================

# ------------------------------------------------------------------------------
# THE OPPORTUNITY DISCOVERY ENGINE
# ------------------------------------------------------------------------------
class OpportunityFeedView(ListView):
    """
    Advanced Job Discovery Engine.
    Uses Semantic Synonym Expansion and Weighted Database Scoring.
    """
    model = JobPost
    template_name = 'opportunities/public/feed.html'
    context_object_name = 'opportunities'
    paginate_by = 24

    def get_queryset(self):
        # 1. BASE QUERY (Highly Optimized)
        base_queryset = JobPost.objects.filter(
            status=JobPost.Status.ACTIVE
        ).select_related(
            'posted_by', 'company'
        ).prefetch_related(
            'required_skills'
        )

        form = OpportunitySearchForm(self.request.GET)

        # If the form isn't valid or has no data, return the newest active jobs
        if not form.is_valid():
            return base_queryset.order_by('-published_at', '-created_at')

        # 2. EXTRACT FORM DATA
        q = form.cleaned_data.get('q', '').strip()
        location = form.cleaned_data.get('location', '').strip()
        job_type = form.cleaned_data.get('job_type')
        level = form.cleaned_data.get('level')
        days_posted = form.cleaned_data.get('days_posted')
        is_remote = form.cleaned_data.get('is_remote')
        requires_challenge = form.cleaned_data.get('requires_challenge')

        # ==============================================================================
        # LAYER 1: STRICT SHIELD FILTERS (Dropdowns & Checkboxes)
        # ==============================================================================
        if is_remote:
            base_queryset = base_queryset.filter(is_remote=True)
        if requires_challenge:
            base_queryset = base_queryset.filter(requires_challenge=True)
        if job_type:
            base_queryset = base_queryset.filter(job_type=job_type)
        if level:
            base_queryset = base_queryset.filter(level=level)
        if location:
            # Check both the specific location field AND if it's remote
            base_queryset = base_queryset.filter(
                Q(location__icontains=location) | Q(is_remote=True)
            )
        if days_posted:
            cutoff_date = timezone.now() - timedelta(days=int(days_posted))
            base_queryset = base_queryset.filter(published_at__gte=cutoff_date)

        # ==============================================================================
        # LAYER 2: THE "SMART" KEYWORD ENGINE
        # ==============================================================================
        if q:
            # 1. Extract Exact Phrases (e.g., "Software Engineer")
            exact_phrases = re.findall(r'"([^"]*)"', q)

            # 2. Clean text and split remaining words
            cleaned_query = re.sub(r'"([^"]*)"', '', q)
            cleaned_query = re.sub(r'[^\w\s]', '', cleaned_query).lower()
            base_words = [w for w in cleaned_query.split() if len(w) > 2]

            if not base_words and not exact_phrases:
                base_words = [q.lower()]

            expanded_words = set(base_words)

            # 3. THE SYNONYM MATRIX (Teach the engine about your industry)
            SYNONYM_MATRIX = {
                'frontend': ['react', 'vue', 'angular', 'ui', 'css', 'tailwind', 'html'],
                'backend': ['django', 'python', 'node', 'api', 'postgres', 'sql', 'database'],
                'fullstack': ['react', 'django', 'node', 'frontend', 'backend', 'full-stack'],
                'design': ['figma', 'ui/ux', 'product designer', 'graphics', 'illustrator'],
                'marketing': ['seo', 'growth', 'content', 'social media', 'sales'],
                'crypto': ['web3', 'blockchain', 'solidity', 'smart contract', 'eth'],
                'mobile': ['flutter', 'react native', 'ios', 'android', 'swift', 'kotlin']
            }

            for word in base_words:
                for key, synonyms in SYNONYM_MATRIX.items():
                    if word == key or word in synonyms:
                        expanded_words.update(synonyms)
                        expanded_words.add(key)

            expanded_words.update(exact_phrases)

            # ==============================================================================
            # LAYER 3: WEIGHTED RELEVANCE SCORING
            # ==============================================================================
            annotations = {}
            relevance_fields = []

            if expanded_words:
                for i, word in enumerate(expanded_words):
                    # 🥇 +100 Points: High Intent (Title matches or Company Name)
                    high_key = f'match_high_{i}'
                    annotations[high_key] = Case(
                        When(
                            Q(title__icontains=word) |
                            Q(company__name__icontains=word) |
                            Q(external_company_name__icontains=word) |
                            Q(required_skills__name__icontains=word),  # We keep this just in case they use it!
                            then=Value(100)
                        ), default=Value(0), output_field=IntegerField()
                    )

                    # 🥈 +30 Points: Medium Intent (Challenge Description or Company Sector)
                    med_key = f'match_med_{i}'
                    annotations[med_key] = Case(
                        When(
                            Q(challenge_description__icontains=word) |
                            Q(company__sector__icontains=word),
                            then=Value(30)
                        ), default=Value(0), output_field=IntegerField()
                    )

                    # 🥉 +10 Points: Low Intent (Mentioned deep in the description text)
                    low_key = f'match_low_{i}'
                    annotations[low_key] = Case(
                        When(
                            Q(description__icontains=word),
                            then=Value(10)
                        ), default=Value(0), output_field=IntegerField()
                    )

                    relevance_fields.extend([high_key, med_key, low_key])

                # ==============================================================================
                # LAYER 4: SCORE COMPILATION & HYBRID SORT
                # ==============================================================================
                # Add all the scores together dynamically
                total_relevance_expr = reduce(operator.add, (F(field) for field in relevance_fields))

                base_queryset = base_queryset.annotate(
                    **annotations
                ).annotate(
                    search_relevance=total_relevance_expr
                ).filter(
                    search_relevance__gt=0  # Hide jobs that score 0
                ).order_by('-search_relevance', '-published_at')  # 🚀 Best Match first, then newest!

        else:
            # BROWSE MODE: No keyword searched, just apply the dropdown filters and sort by newest
            base_queryset = base_queryset.order_by('-published_at', '-created_at')

        # distinct() ensures jobs don't show up twice if multiple words matched
        return base_queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass the form back to the template so the user's search text stays in the input boxes
        context['search_form'] = OpportunitySearchForm(self.request.GET)
        return context

class OpportunityDetailView(DetailView):
    model = JobPost
    template_name = 'opportunities/public/detail.html'
    context_object_name = 'job'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return JobPost.objects.filter(status=JobPost.Status.ACTIVE).select_related(
            'posted_by', 'company'
        ).prefetch_related('required_skills')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Use the thread-safe method from our newly upgraded models.py
        obj.increment_view()
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            # Check if user already applied
            context['has_applied'] = JobApplication.objects.filter(
                job=self.object, applicant=self.request.user
            ).exists()

            # 🔥 CRITICAL FIX: Pass the user's projects to the template so they can attach them for Challenge Mode!
            context['my_projects'] = Project.objects.filter(profile__user=self.request.user)

        return context


# ==============================================================================
# 3. APPLICATION LOGIC (THE LINK)
# ==============================================================================

@login_required
@require_POST
def link_profile_action(request, slug):
    """
    Handles internal applications and Challenge Mode logic.
    """
    job = get_object_or_404(JobPost, slug=slug, status=JobPost.Status.ACTIVE)

    if job.posted_by == request.user:
        messages.error(request, "You cannot apply to your own post.")
        return redirect('opportunities:detail', slug=slug)

    # 1. Capture Pitch (Updated to 2000 chars)
    pitch_note = request.POST.get('cover_note', '').strip()[:2000]

    # 2. Handle Attached Project (Challenge Mode)
    attached_project_id = request.POST.get('attached_project')
    attached_project = None

    if attached_project_id:
        attached_project = Project.objects.filter(id=attached_project_id, profile__user=request.user).first()

    # 3. Strict Challenge Validation
    if job.requires_challenge and not attached_project:
        messages.error(request, "❌ This role requires you to attach a specific Project as Proof of Work.")
        return redirect('opportunities:detail', slug=slug)

    # 4. Create Application safely
    try:
        with transaction.atomic():
            application, created = JobApplication.objects.get_or_create(
                job=job,
                applicant=request.user,
                defaults={
                    'status': JobApplication.Status.LINKED,
                    'cover_note': pitch_note,
                    'attached_project': attached_project
                }
            )

        if created:
            messages.success(request, "⚡ Application Submitted Successfully!")
        else:
            messages.info(request, "You have already applied for this role.")

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect('opportunities:detail', slug=slug)


@login_required
def track_external_application(request, slug):
    """
    Tracks clicks on 'Apply Externally' buttons and safely redirects.
    """
    job = get_object_or_404(JobPost, slug=slug)

    if job.external_url:
        # Optionally, log external clicks as pseudo-applications for metrics:
        if not JobApplication.objects.filter(job=job, applicant=request.user).exists():
            JobApplication.objects.create(
                job=job, applicant=request.user, status=JobApplication.Status.LINKED, cover_note="Redirected Externally"
            )
        return redirect(job.external_url)

    return redirect('opportunities:detail', slug=slug)


# ==============================================================================
# 4. RECRUITER DASHBOARD
# ==============================================================================

from django.db.models import Prefetch
# Adjust this import to match the app where your new unified profile models live
from profiles.models import ProfileHeadline, Skill, WorkExperience
from django.db.models import Prefetch
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

# Adjust this import to match the app where your new unified profile models live
from profiles.models import ProfileHeadline, Skill, WorkExperience
from .models import JobApplication, JobPost

class ApplicantBoardView(LoginRequiredMixin, ListView):
    model = JobApplication
    template_name = 'opportunities/company/applicant_board.html'
    context_object_name = 'applications'

    def dispatch(self, request, *args, **kwargs):
        self.job = get_object_or_404(JobPost, slug=self.kwargs['slug'])

        if not can_manage_job(request.user, self.job):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # 🔥 MAGICAL QUERY: Fetches applications + all unified profile data in ~4 queries total!
        return JobApplication.objects.filter(job=self.job).select_related(
            'applicant', 'applicant__portfolio', 'attached_project'
        ).prefetch_related(
            Prefetch(
                'applicant__portfolio__headlines',
                queryset=ProfileHeadline.objects.filter(is_primary=True),
                to_attr='primary_headline'
            ),
            Prefetch(
                'applicant__portfolio__skills',
                queryset=Skill.objects.filter(status='MASTERED').order_by('-progress_bar'),
                to_attr='mastered_skills'
            ),
            Prefetch(
                'applicant__portfolio__experiences',
                queryset=WorkExperience.objects.order_by('-is_current', '-start_date'),
                to_attr='ordered_experiences'
            )
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['job'] = self.job
        context['total_linked'] = self.get_queryset().count()
        return context


@login_required
@require_POST
def update_application_status(request, application_id):
    """
    Note: application_id is safe here because it refers to the JobApplication ID, not the JobPost.
    Redirect uses job.slug.
    """
    application = get_object_or_404(JobApplication, pk=application_id)
    job = application.job

    if not can_manage_job(request.user, job):
        return HttpResponseForbidden()

    new_status = request.POST.get('status')
    if new_status in dict(JobApplication.Status.choices):
        application.status = new_status
        application.save(update_fields=['status'])

        if new_status == 'SHORTLISTED':
            messages.success(request,
                             f"⭐ {application.applicant.get_full_name() or application.applicant.username} Shortlisted")
        elif new_status == 'REJECTED':
            messages.info(request, "Application Rejected")

    return redirect('opportunities:applicant_board', slug=job.slug)


@login_required
def inspect_applicant_profile(request, application_id):
    """
    Marks application as VIEWED when the recruiter clicks to see the profile.
    application_id refers to the JobApplication ID. Redirects use job.slug or user profile absolute url.
    """
    application = get_object_or_404(JobApplication, pk=application_id)
    job = application.job

    if can_manage_job(request.user, job) and application.status == JobApplication.Status.LINKED:
        application.status = JobApplication.Status.VIEWED
        application.save(update_fields=['status'])

    # Safely route to applicant's profile
    if hasattr(application.applicant, 'get_absolute_url'):
        return redirect(application.applicant.get_absolute_url())
    else:
        messages.success(request, f"Reviewing {application.applicant.username}'s application.")
        return redirect('opportunities:applicant_board', slug=job.slug)


# Make sure to import the new form at the top
from .forms import PublicOpportunitySubmissionForm


class PublicOpportunityCreateView(CreateView):
    """
    Open view for ANYONE to post a job.
    Logged-in users get redirected to the advanced Workspace view.
    """
    model = JobPost
    form_class = PublicOpportunitySubmissionForm
    template_name = 'opportunities/company/create_opportunity.html'  # Create this template next
    success_url = reverse_lazy('opportunities:feed')

    def dispatch(self, request, *args, **kwargs):
        # If they are already logged in, send them to the powerful workspace creator
        if request.user.is_authenticated:
            messages.info(request, "Welcome back! You've been redirected to your workspace to post.")
            return redirect('opportunities:create')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            opportunity = form.save(commit=False)

            # 1. Assign Guest Context
            opportunity.posted_by = None
            opportunity.company = None
            opportunity.is_official_admin_post = False

            # 2. Force External and Pending
            opportunity.is_external = True
            opportunity.status = JobPost.Status.PENDING  # Requires Admin Approval

            opportunity.save()
            form.save_m2m()

        messages.success(
            self.request,
            "🎉 Your opportunity has been submitted and is pending admin approval! "
            "We will reach out to you once it is live."
        )
        return super().form_valid(form)


# ==============================================================================
# 5. INDIVIDUAL USER JOB MANAGEMENT (New System)
# ==============================================================================

class UserJobCreateView(LoginRequiredMixin, CreateView):
    """Create a job as an individual user (not company)."""
    model = JobPost
    form_class = OpportunitySubmissionForm
    template_name = 'opportunities/user/create_opportunity.html'
    success_url = reverse_lazy('opportunities:user_job_management')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            opportunity = form.save(commit=False)
            opportunity.posted_by = self.request.user
            # Force individual user posting (not company)
            opportunity.company = None
            opportunity.is_official_admin_post = False

            if opportunity.external_url:
                opportunity.is_external = True

            # Force pending for non-admins
            is_admin = getattr(self.request.user, 'role', None) == 'ADMIN' or self.request.user.is_staff
            if not is_admin:
                opportunity.status = JobPost.Status.PENDING

            opportunity.save()
            form.save_m2m()

        messages.success(self.request, "🚀 Job posted successfully!")
        return super().form_valid(form)


class UserJobManagementView(LoginRequiredMixin, ListView):
    """Main dashboard for individual users to manage their posted jobs."""
    model = JobPost
    template_name = 'opportunities/user/my_opportunities.html'
    context_object_name = 'jobs'
    paginate_by = 12

    def get_queryset(self):
        # Only show jobs posted by this user (not company jobs)
        return JobPost.objects.filter(
            posted_by=self.request.user,
            company=None  # Exclude company jobs
        ).select_related('posted_by').annotate(
            applicant_count=Count('applications')
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_jobs'] = self.get_queryset().count()
        context['active_jobs'] = self.get_queryset().filter(status='ACTIVE').count()
        context['pending_jobs'] = self.get_queryset().filter(status='PENDING').count()
        
        # Add user's job applications
        from .models import JobApplication
        context['my_applications'] = JobApplication.objects.filter(
            applicant=self.request.user
        ).select_related('job', 'job__company').order_by('-created_at')
        
        return context


class UserJobUpdateView(LoginRequiredMixin, UpdateView):
    """Edit a job posted by individual user."""
    model = JobPost
    form_class = OpportunitySubmissionForm
    template_name = 'opportunities/user/edit_opportunity.html'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return JobPost.objects.filter(
            posted_by=self.request.user,
            company=None
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            opportunity = form.save(commit=False)
            # Ensure it stays as user post (not company)
            opportunity.company = None
            opportunity.is_official_admin_post = False
            opportunity.save()
            form.save_m2m()

        messages.success(self.request, "✅ Job updated successfully!")
        return redirect('opportunities:user_job_management')


class UserJobDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a job posted by individual user."""
    model = JobPost
    template_name = 'opportunities/user/delete_opportunity.html'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('opportunities:user_job_management')

    def get_queryset(self):
        return JobPost.objects.filter(
            posted_by=self.request.user,
            company=None
        )

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "🗑️ Job deleted successfully!")
        return super().delete(request, *args, **kwargs)


class UserApplicantBoardView(LoginRequiredMixin, DetailView):
    """View and manage applicants for a user's posted job."""
    model = JobPost
    template_name = 'opportunities/user/applicant_board.html'
    slug_url_kwarg = 'slug'
    context_object_name = 'job'

    def dispatch(self, request, *args, **kwargs):
        self.job = get_object_or_404(JobPost, slug=self.kwargs['slug'])

        if not can_manage_job(request.user, self.job):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return JobPost.objects.filter(
            posted_by=self.request.user,
            company=None
        ).prefetch_related('applications__applicant')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = self.object
        applications = job.applications.all().order_by('-created_at')

        # Group by status - using correct JobApplication.Status values
        context['applications'] = applications
        context['pending_count'] = applications.filter(status=JobApplication.Status.LINKED).count()
        context['reviewing_count'] = applications.filter(status=JobApplication.Status.VIEWED).count()
        context['accepted_count'] = applications.filter(status=JobApplication.Status.SHORTLISTED).count()
        context['rejected_count'] = applications.filter(status=JobApplication.Status.REJECTED).count()

        return context


# ==============================================================================
# 6. TELEGRAM/SOCIAL PREVIEW IMAGE GENERATOR
# ==============================================================================

def opportunity_og_image(request, slug):
    """
    Generates a world-class futuristic OpenGraph image for job opportunities.
    Features minimal design, company logo, optimized colors, and clean typography.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    job = get_object_or_404(JobPost, slug=slug, status=JobPost.Status.ACTIVE)
    
    # 1. Create a blank canvas with optimized futuristic gradient
    base_img = Image.new("RGB", (1200, 630), "#0F172A")
    draw = ImageDraw.Draw(base_img)
    
    # 2. Draw futuristic gradient background
    # Top section: Deep gradient
    for y in range(0, 350):
        alpha = int(255 * (1 - y / 350))
        color = (
            int(15 + (10 - 15) * (y / 350)),  # R
            int(23 + (102 - 23) * (y / 350)),  # G  
            int(42 + (194 - 42) * (y / 350))   # B
        )
        draw.rectangle([(0, y), (1200, y + 1)], fill=color)
    
    # Bottom section: Clean white
    draw.rectangle([(0, 350), (1200, 630)], fill="#FFFFFF")
    draw.line([(0, 350), (1200, 350)], fill="#0A66C2", width=6)
    
    # 3. Load fonts with fallback (must be done before drawing text)
    font_large = None
    font_medium = None
    font_small = None
    
    try:
        font_path = finders.find('fonts/Inter_18pt-Bold.ttf')
        if not font_path and hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
            backup_path = os.path.join(settings.STATIC_ROOT, 'fonts', 'Inter_18pt-Bold.ttf')
            if os.path.exists(backup_path):
                font_path = backup_path
        
        if font_path:
            font_large = ImageFont.truetype(font_path, 56)
            font_medium = ImageFont.truetype(font_path, 32)
            font_small = ImageFont.truetype(font_path, 24)
        else:
            raise Exception("Font not found")
    except Exception as e:
        logger.warning(f"Font loading failed: {e}")
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # 4. Draw Company Logo (if available)
    logo_y = 80
    logo_drawn = False
    
    if job.get_company_logo():
        try:
            from django.core.files.storage import default_storage
            logo_url = job.get_company_logo()
            
            # Handle both URL and file paths
            if logo_url.startswith('http'):
                # It's a URL, try to download it
                import requests
                response = requests.get(logo_url, timeout=5)
                if response.status_code == 200:
                    logo = Image.open(io.BytesIO(response.content))
                    logo = logo.resize((100, 100), Image.Resampling.LANCZOS)
                    # Create rounded rectangle mask
                    mask = Image.new('L', (100, 100), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.rounded_rectangle([(0, 0), (100, 100)], radius=20, fill=255)
                    # Paste with white border
                    border = Image.new("RGBA", (110, 110), (0, 0, 0, 0))
                    border_draw = ImageDraw.Draw(border)
                    border_draw.rounded_rectangle([(0, 0), (110, 110)], radius=25, fill="#FFFFFF")
                    base_img.paste(border, (50, logo_y - 5), border)
                    base_img.paste(logo, (55, logo_y), mask)
                    logo_drawn = True
            else:
                # It's a relative path, try to open from storage
                # Use the company's logo field directly if it's a FileField
                if job.company and job.company.logo:
                    try:
                        with job.company.logo.open('rb') as logo_file:
                            logo = Image.open(logo_file)
                            logo = logo.resize((100, 100), Image.Resampling.LANCZOS)
                            # Create rounded rectangle mask
                            mask = Image.new('L', (100, 100), 0)
                            mask_draw = ImageDraw.Draw(mask)
                            mask_draw.rounded_rectangle([(0, 0), (100, 100)], radius=20, fill=255)
                            # Paste with white border
                            border = Image.new("RGBA", (110, 110), (0, 0, 0, 0))
                            border_draw = ImageDraw.Draw(border)
                            border_draw.rounded_rectangle([(0, 0), (110, 110)], radius=25, fill="#FFFFFF")
                            base_img.paste(border, (50, logo_y - 5), border)
                            base_img.paste(logo, (55, logo_y), mask)
                            logo_drawn = True
                    except Exception as e:
                        logger.warning(f"Failed to load company logo from field: {e}")
                elif job.external_company_logo:
                    try:
                        with job.external_company_logo.open('rb') as logo_file:
                            logo = Image.open(logo_file)
                            logo = logo.resize((100, 100), Image.Resampling.LANCZOS)
                            # Create rounded rectangle mask
                            mask = Image.new('L', (100, 100), 0)
                            mask_draw = ImageDraw.Draw(mask)
                            mask_draw.rounded_rectangle([(0, 0), (100, 100)], radius=20, fill=255)
                            # Paste with white border
                            border = Image.new("RGBA", (110, 110), (0, 0, 0, 0))
                            border_draw = ImageDraw.Draw(border)
                            border_draw.rounded_rectangle([(0, 0), (110, 110)], radius=25, fill="#FFFFFF")
                            base_img.paste(border, (50, logo_y - 5), border)
                            base_img.paste(logo, (55, logo_y), mask)
                            logo_drawn = True
                    except Exception as e:
                        logger.warning(f"Failed to load external company logo: {e}")
        except Exception as e:
            logger.warning(f"Failed to load company logo: {e}")
    
    # Fallback: Draw company initial if logo not drawn
    if not logo_drawn:
        company_name = job.get_company_name()
        if company_name:
            initial = company_name[0].upper() if company_name else "C"
            # Draw circle with initial
            circle = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            circle_draw = ImageDraw.Draw(circle)
            circle_draw.ellipse((0, 0, 100, 100), fill="#0A66C2")
            base_img.paste(circle, (55, logo_y), circle)
            # Draw initial
            initial_font = font_large if font_large else font_medium
            if initial_font:
                # Calculate text position to center it
                bbox = draw.textbbox((0, 0), initial, font=initial_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = 55 + (100 - text_width) // 2
                y = logo_y + (100 - text_height) // 2
                draw.text((x, y), initial, fill="#FFFFFF", font=initial_font)
    
    # 5. Draw Job Title
    title = job.title
    if len(title) > 45:
        title = title[:42] + "..."
    draw.text((180, 90), title, fill="#FFFFFF", font=font_large)
    
    # 6. Draw Company Name
    company = job.get_company_name()
    if len(company) > 35:
        company = company[:32] + "..."
    draw.text((180, 160), company, fill="#94A3B8", font=font_small)
    
    # 7. Draw Job Type Badge
    job_type = job.get_job_type_display()
    if len(job_type) > 20:
        job_type = job_type[:17] + "..."
    badge_x = 180
    badge_y = 200
    badge_width = font_small.getlength(job_type) + 40
    draw.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_width, badge_y + 36)], radius=18, fill="#0A66C2")
    draw.text((badge_x + 20, badge_y + 6), job_type, fill="#FFFFFF", font=font_small)
    
    # 8. Draw Location (if available)
    if job.location:
        location_text = job.location
        if len(location_text) > 30:
            location_text = location_text[:27] + "..."
        draw.text((badge_x + badge_width + 20, badge_y + 6), f"📍 {location_text}", fill="#94A3B8", font=font_small)
    
    # 9. Draw Bottom Section - Job Details
    # Draw CoreLink branding
    draw.text((40, 400), "CoreLink", fill="#0A66C2", font=font_medium)
    draw.text((40, 450), "Opportunities", fill="#64748B", font=font_small)
    
    # Draw job type icon and text
    type_icons = {
        'FULL_TIME': '💼',
        'PART_TIME': '⏰',
        'CONTRACT': '📝',
        'GIG': '⚡',
        'CHALLENGE': '🏆',
        'INTERNSHIP': '🎓',
        'ADVISORY': '🤝',
        'VOLUNTEER': '❤️',
        'COFOUNDER': '🚀'
    }
    icon = type_icons.get(job.job_type, '💼')
    draw.text((400, 400), f"{icon} {job.get_job_type_display()}", fill="#0F172A", font=font_small)
    
    # Draw level if available
    if job.level and job.level != 'ANY':
        draw.text((400, 440), f"📊 {job.get_level_display()}", fill="#64748B", font=font_small)
    
    # Draw salary if available
    if job.salary_range_display and job.salary_range_display != "Competitive":
        salary_text = job.salary_range_display
        if len(salary_text) > 25:
            salary_text = salary_text[:22] + "..."
        draw.text((400, 480), f"💰 {salary_text}", fill="#059669", font=font_small)
    
    # 10. Draw decorative accent
    draw.rectangle([(1100, 400), (1150, 580)], fill="#0A66C2")
    draw.rectangle([(1105, 405), (1145, 575)], fill="#FFFFFF")
    
    # 11. Export image
    buffer = io.BytesIO()
    base_img.save(buffer, format="JPEG", quality=95)
    return HttpResponse(buffer.getvalue(), content_type="image/jpeg")