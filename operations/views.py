from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model

# --- UNIFIED MODELS IMPORTS ---
from profiles.models.new_unified_profile import UserProfile, Skill, Credential
from profiles.models import FounderProfile, Company
from opportunities.models import JobPost, JobApplication

User = get_user_model()


# --- PART 1: THE INSPECTOR VIEW ---

@staff_member_required
def inspect_user(request, user_id):
    """
    Renders the FRONTEND dashboard templates, but populated with
    the TARGET USER'S data, wrapping it in the Inspector Context.
    (Now 10x faster using the Unified Profile)
    """
    target_user = get_object_or_404(User, pk=user_id)

    # 1. Fetch Unified Profile
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    # 2. Build Unified Context (Identical to what we did in profiles.views)
    context = {
        'target_user': target_user,  # Triggers Admin God Bar
        'user': target_user,  # Satisfies template variables
        'is_inspector': True,
        'portfolio': profile,  # Template expects 'portfolio' not 'profile'
        'avatar_url': target_user.get_avatar_url,
        'cover_image_url': target_user.get_cover_image_url,
        'social_links': target_user.social_links.all(),
        'contact_methods': target_user.contact_methods.all(),
        'email_unverified': not target_user.email or not getattr(target_user, 'is_email_verified', True),

        # New Unified Relations
        'headlines': profile.headlines.all().order_by('-is_primary'),
        'skills': profile.skills.all(),
        'experiences': profile.experiences.all().order_by('-start_date'),
        'projects': profile.projects.all().order_by('order', '-created_at'),
        'credentials': profile.credentials.all().order_by('-issue_date'),
        'posts': profile.content_posts.all().order_by('-created_at'),
        'preferences': profile.job_preferences.all(),
    }

    # 3. Route to proper Template
    if target_user.role == 'EXPERT':
        return render(request, 'dashboard/main_dashboard.html', context)

    elif target_user.role == 'VISIONARY':
        # Safely map to Visionary variables so the template doesn't crash
        context.update({
            'targets': profile.skills.filter(status='LEARNING'),
            'logs': profile.content_posts.filter(post_type='GROWTH_LOG'),
            'blocks': profile.content_posts.filter(post_type='VISION_BLOCK'),
            'certifications': profile.credentials.filter(credential_type='CERTIFICATE')
        })
        return render(request, 'dashboard/main_dashboard.html', context)

    elif target_user.role == 'ADMIN':
        # Admin users see the unified dashboard like experts
        return render(request, 'dashboard/main_dashboard.html', context)

    elif target_user.role == 'FOUNDER':
        membership = target_user.company_memberships.filter(is_active=True).first()
        company = membership.company if membership else None
        context.update({
            'company': company,
            'company_name': company.name if company else "My Enterprise",
            'my_opportunities': JobPost.objects.filter(posted_by=target_user).select_related('company').order_by(
                '-created_at'),
            'my_applications': JobApplication.objects.filter(applicant=target_user).select_related('job').order_by(
                '-created_at'),
        })
        return render(request, 'dashboard/company/admin_dashboard.html', context)

    return HttpResponse("Unknown Role", status=400)


# --- PART 2: THE POOL BROWSER ---

@staff_member_required
def ops_pool_browser(request, pool_type):
    """
    Dynamic Browser: Handles Users and Companies.
    """
    if pool_type.upper() == 'USER':
        users = User.objects.all().select_related('portfolio')
        context = {
            'users': users,
            'pool_type': 'USER',
            'pool_title': 'Users',
            'total_count': users.count()
        }
        return render(request, 'ops/pool_browser.html', context)
    elif pool_type.upper() == 'COMPANY':
        companies = Company.objects.all().prefetch_related('memberships__user')
        context = {
            'companies': companies,
            'pool_type': 'COMPANY',
            'pool_title': 'Companies',
            'total_count': companies.count()
        }
        return render(request, 'ops/pool_browser.html', context)
    else:
        return HttpResponse("Invalid pool type", status=400)


# --- PART 3: HTMX ACTIONS (GOD BAR) ---

@staff_member_required
@require_POST
def toggle_verify(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    user.is_verified = not user.is_verified
    user.save()

    status_color = "bg-emerald-500/20 text-emerald-400 border-emerald-500/50" if user.is_verified else "bg-slate-800 text-slate-400 border-slate-700"
    label = "Verified" if user.is_verified else "Unverified"

    return HttpResponse(f"""
        <button hx-post="/ops/toggle-verify/{user.id}/" hx-swap="outerHTML"
                class="flex items-center gap-2 px-4 py-2 rounded-xl font-bold transition-all {status_color} border">
            <i data-lucide="badge-check" class="h-4 w-4"></i> {label}
        </button>
    """)


@staff_member_required
@require_POST
def toggle_active(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    user.is_active = not user.is_active
    user.save()

    status_color = "bg-blue-500/20 text-blue-400 border-blue-500/50" if user.is_active else "bg-red-500/20 text-red-400 border-red-500/50"
    label = "Active" if user.is_active else "Banned"

    return HttpResponse(f"""
        <button hx-post="/ops/toggle-active/{user.id}/" hx-swap="outerHTML"
                class="flex items-center gap-2 px-4 py-2 rounded-xl font-bold transition-all {status_color} border">
            <i data-lucide="power" class="h-4 w-4"></i> {label}
        </button>
    """)


# --- 1. UNIVERSAL RATING SYSTEM ---
@staff_member_required
@require_POST
def update_rating(request, user_id, rating_value):
    """Admin dynamically updates the Universal Profile Rating."""
    target_user = get_object_or_404(User, pk=user_id)

    # We no longer need if/else for expert/visionary. Everyone has ONE profile!
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    current_val = profile.admin_rating

    # Toggle Logic (Clicking same star resets to 0)
    if current_val == int(rating_value):
        new_rating = 0
    else:
        new_rating = int(rating_value)

    profile.admin_rating = new_rating
    profile.save(update_fields=['admin_rating'])

    return render(request, 'ops/partials/rating_stars.html', {
        'target_user': target_user,
        'current_rating': new_rating,
        'is_inspector': True
    })


# --- 2. APPROVAL SYSTEM (SKILLS & CREDENTIALS) ---
@staff_member_required
@require_POST
def toggle_cluster_item_status(request, model_type, item_id):
    """
    Toggles Verification Status for Skills and Credentials.
    """
    context = {'is_inspector': True}

    if model_type == 'skill':
        item = get_object_or_404(Skill, id=item_id)
        # Toggle String Logic
        item.admin_status = 'PENDING' if item.admin_status == 'VERIFIED' else 'VERIFIED'
        item.save(update_fields=['admin_status'])

        context['skills'] = item.profile.skills.all()
        # Ensure you renamed your partials folder to 'unified' as discussed earlier!
        return render(request, 'dashboard/unified/partials/skills_list.html', context)

    elif model_type == 'cred':
        item = get_object_or_404(Credential, id=item_id)
        # Toggle Boolean Logic (Unified Credential uses a boolean field)
        item.is_admin_verified = not item.is_admin_verified
        item.save(update_fields=['is_admin_verified'])

        context['credentials'] = item.profile.credentials.all()
        return render(request, 'dashboard/unified/partials/credential_list.html', context)

    return HttpResponse("Invalid Type", status=400)