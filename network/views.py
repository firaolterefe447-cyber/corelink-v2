# ==============================================================================
# 🚀 PURE CORE ENGINE IMPORTS (NO EXTENSIONS REQUIRED)
# ==============================================================================
import re
import difflib
import operator
import random
from functools import reduce, lru_cache
from datetime import timedelta
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import connection

from django.db.models import (
    Q, F, Case, When, Value, IntegerField, FloatField, Max, ExpressionWrapper, Prefetch, Count
)
from django.db.models.functions import Coalesce, Greatest, Cast, Now, ExtractDay

# Standard Postgres Full-Text Search
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.aggregates import StringAgg

# Local App Imports
from .models import NetworkPost
from .forms import NetworkPostForm

# For Company Nexus
from profiles.models import Company

try:
    from workspace.models import ChatMessage  # Preserving Inbox Badge Logic
except ImportError:
    pass

CustomUser = get_user_model()


# ==============================================================================
# 🌌 THE OMNI-INDUSTRY SUPREME ORACLE (100/10 NLP ARCHITECTURE)
# ==============================================================================
class OmniIndustryOracle:
    """
    An Enterprise-Grade NLP Graph. Spans across ALL human professional sectors.
    Understands abbreviations, local slang, and deep semantic relationships.
    """

    STOP_WORDS = {
        'i', 'need', 'want', 'looking', 'for', 'a', 'an', 'the', 'who', 'knows',
        'can', 'someone', 'help', 'me', 'with', 'and', 'or', 'in', 'to', 'is', 'are'
    }

    # 🌍 Omni-Industry Abbreviations & Local Context Engine
    PREFIX_MAP = {
        'dr': 'doctor', 'rn': 'nurse', 'cpa': 'accountant', 'hr': 'human resources',
        'pr': 'public relations', 'ceo': 'executive', 'cto': 'executive',
        'py': 'python', 'js': 'javascript', 'ml': 'machine learning', 'ai': 'artificial intelligence',
        'ux': 'user experience', 'ui': 'user interface', 'dev': 'developer', 'eng': 'engineer',
        'adis': 'addis', 'abeba': 'ababa', 'sheger': 'addis ababa', 'finfinne': 'addis ababa',
        'etopia': 'ethiopia', 'telebirr': 'fintech', 'chapa': 'fintech', 'cbe': 'banking'
    }

    # 🌌 THE MASSIVE OMNI-INDUSTRY SEMANTIC GRAPH
    KNOWLEDGE_GRAPH = {
        'medical': ['doctor', 'nurse', 'surgeon', 'pharmacy', 'pharmacist', 'clinic', 'hospital'],
        'healthcare': ['medical', 'hospital', 'clinic', 'wellness', 'psychology', 'therapist'],
        'law': ['lawyer', 'attorney', 'legal', 'corporate law', 'advocate', 'court', 'litigation'],
        'ngo': ['non-profit', 'humanitarian', 'united nations', 'usaid', 'development', 'grant writing'],
        'agriculture': ['farming', 'agritech', 'agronomy', 'coffee export', 'supply chain', 'sustainability'],
        'logistics': ['supply chain', 'import', 'export', 'freight', 'customs', 'warehouse'],
        'engineering': ['civil engineering', 'mechanical', 'electrical', 'structural', 'cad', 'architect'],
        'construction': ['builder', 'contractor', 'architecture', 'project management', 'real estate'],
        'finance': ['accounting', 'auditing', 'banking', 'investment', 'crypto', 'financial modeling', 'fintech'],
        'marketing': ['seo', 'branding', 'digital marketing', 'social media', 'growth hacking', 'sales'],
        'business': ['entrepreneur', 'founder', 'management', 'executive', 'startup', 'strategy', 'hr'],
        'creative': ['art', 'photography', 'filmmaking', 'writing', 'music', 'video editing'],
        'design': ['graphic design', 'ui/ux', 'product design', 'figma', 'photoshop', 'branding'],
        'media': ['journalism', 'reporter', 'broadcasting', 'news', 'content creation', 'copywriting'],
        'education': ['teacher', 'professor', 'tutor', 'curriculum', 'school', 'university', 'e-learning'],
        'developer': ['software engineer', 'programmer', 'coder', 'backend', 'frontend', 'fullstack'],
        'frontend': ['react', 'vue', 'angular', 'javascript', 'html', 'css', 'tailwind'],
        'backend': ['python', 'django', 'node', 'java', 'go', 'ruby', 'api', 'database', 'sql', 'postgresql'],
        'ai': ['machine learning', 'data science', 'deep learning', 'nlp', 'llm', 'data analysis']
    }

    GLOBAL_VOCABULARY = list(KNOWLEDGE_GRAPH.keys()) + [
        item for sublist in KNOWLEDGE_GRAPH.values() for item in sublist
    ]

    @classmethod
    @lru_cache(maxsize=10000)
    def process_omni_intent(cls, raw_query):
        """The 4-Stage Mind-Reading Pipeline."""
        query = raw_query.lower().strip()

        # 🕵️‍♂️ STAGE 1: HR & CONSTRAINTS EXTRACTION
        exp_match = re.search(r'(\d+)\+?\s*(years|yrs|yr)', query)
        min_experience = int(exp_match.group(1)) if exp_match else None
        is_hiring = any(word in query for word in ['hire', 'hiring', 'job', 'freelance', 'contract', 'opportunity'])
        is_senior = any(word in query for word in ['senior', 'lead', 'expert', 'director', 'head', 'chief'])
        is_junior = any(word in query for word in ['junior', 'intern', 'fresher', 'student', 'assistant'])

        exact_phrases = re.findall(r'"([^"]*)"', query)
        locations = re.findall(r'location:([^\s]+)', query)
        skills = re.findall(r'skill:([^\s]+)', query)

        cleaned = re.sub(r'"([^"]*)"|location:[^\s]+|skill:[^\s]+|\d+\+?\s*(years|yrs|yr)|[^\w\s]', '', query)

        direct_keywords = set(exact_phrases)
        semantic_keywords = set()
        search_locations = set(locations)

        # Local Context Resolver
        if any(w in cleaned for w in ['sheger', 'finfinne', 'addis']):
            search_locations.update(['addis ababa', 'addis', 'aa'])

        # 🧠 STAGE 2: OMNI-INDUSTRY WORD PROCESSING
        words = cleaned.split()
        for word in words:
            if word in cls.STOP_WORDS:
                continue

            if word in cls.PREFIX_MAP:
                word = cls.PREFIX_MAP[word]
            elif len(word) >= 4:
                close_matches = difflib.get_close_matches(word, cls.GLOBAL_VOCABULARY, n=1, cutoff=0.75)
                if close_matches:
                    word = close_matches[0]

            if len(word) > 1:
                direct_keywords.add(word)

            # 🌌 STAGE 3: THE SEMANTIC GRAPH TRAVERSAL
            for core_concept, related_fields in cls.KNOWLEDGE_GRAPH.items():
                if word == core_concept or word in related_fields:
                    semantic_keywords.add(core_concept)
                    semantic_keywords.update(related_fields)

        return (
            " ".join(direct_keywords),
            " ".join(semantic_keywords - direct_keywords),
            list(search_locations),
            skills,
            min_experience,
            is_hiring,
            is_senior,
            is_junior
        )


# ==============================================================================
# 🌍 PART 2: THE PLATINUM-PRIORITY SEARCH ENGINE (UNIFIED 'LEGO BLOCK' SYSTEM)
# ==============================================================================
def nexus_feed(request):
    raw_query = request.GET.get('q', '')
    role_filter = request.GET.get('role', 'ALL')

    # 🛡️ 1. BASE SHIELD
    base_users = CustomUser.objects.filter(
        is_active=True, is_public=True, is_nexus_visible=True
    ).exclude(
        role='ADMIN'
    ).select_related(
        'portfolio'
    ).prefetch_related(
        'company_memberships__company'
    )

    # ⏳ 2a. DB-AGNOSTIC TEMPORAL CALCULATION
    base_users = base_users.annotate(
        raw_inactive_duration=Now() - Coalesce(F('last_login'), F('date_joined'))
    )

    if connection.vendor == 'postgresql':
        days_inactive_expr = ExtractDay('raw_inactive_duration')
    else:
        # SQLite Fallback: 1 Day = 86,400,000,000 microseconds
        days_inactive_expr = ExpressionWrapper(
            Cast(F('raw_inactive_duration'), FloatField()) / 86400000000.0,
            output_field=FloatField()
        )

    # 💎 2b. THE "SMART FEED" GRAVITY (Using Raw AI Score & Freshness)
    scored_users = base_users.annotate(
        days_inactive=days_inactive_expr,
        freshness_boost=Greatest(Value(0.0), Value(15.0) - Cast(F('days_inactive'), FloatField()) / 2.0),

        # NEW: Pull the direct 1-100 Oracle Score instead of manual avatar calculations
        raw_ai_score=Cast(Coalesce('portfolio__oracle_score', Value(0)), FloatField())
    ).annotate(
        # The ultimate ranking value: AI Assessment (1-100) + Recent Activity (0-15)
        total_quality=F('raw_ai_score') + F('freshness_boost')
    )

    # ✨ NEW: SEPARATE SPOTLIGHT USERS (Top tier talent & pinned users)
    # We grab them before any text search filters are applied so they can float at the top
    spotlight_users = scored_users.filter(
        Q(is_selected=True) | Q(raw_ai_score__gte=85)
    ).order_by('-is_selected', '-total_quality')[:4]

    # ✨ TOP 10 USERS (Admin-selected, displayed first in random order)
    top_10_users = list(scored_users.filter(is_top_10=True)[:10])
    random.shuffle(top_10_users)

    if raw_query:
        # 🧠 3. AWAKEN THE OMNI-INDUSTRY ORACLE
        (
            direct_string,
            semantic_string,
            loc_tags, skill_tags,
            min_experience, is_hiring, is_senior, is_junior
        ) = OmniIndustryOracle.process_omni_intent(raw_query)

        # --- APPLY INVISIBLE HR CONSTRAINTS ---
        for loc in loc_tags:
            scored_users = scored_users.filter(
                Q(current_location__icontains=loc) |
                Q(portfolio__location__icontains=loc)
            )
        for sk in skill_tags:
            scored_users = scored_users.filter(portfolio__skills__name__icontains=sk)

        if min_experience:
            scored_users = scored_users.filter(portfolio__years_experience__gte=min_experience)
        elif is_senior:
            scored_users = scored_users.filter(portfolio__years_experience__gte=5)
        elif is_junior:
            scored_users = scored_users.filter(Q(portfolio__years_experience__lte=2) | Q(role='VISIONARY'))

        if is_hiring:
            scored_users = scored_users.filter(portfolio__collaboration_status='OPEN')

        # 🚀 4. THE CARTESIAN COMPRESSION & PLATINUM-PRIORITY VECTORS
        if direct_string or semantic_string:
            scored_users = scored_users.annotate(
                all_skills=StringAgg('portfolio__skills__name', delimiter=' ', distinct=True),
                all_headlines=StringAgg('portfolio__headlines__title', delimiter=' ', distinct=True),
                all_exp_roles=StringAgg('portfolio__experiences__role_title', delimiter=' ', distinct=True),
                all_job_titles=StringAgg('company_memberships__job_title', delimiter=' ', distinct=True),
                all_company_sectors=StringAgg('company_memberships__company__sector', delimiter=' ', distinct=True),
            )

            platinum_vector = (
                    SearchVector('portfolio__current_mission', weight='A') +
                    SearchVector('portfolio__field_of_interest', weight='A') +
                    SearchVector('all_headlines', weight='A')
            )

            gold_vector = (
                    SearchVector('all_skills', weight='A') +
                    SearchVector('all_exp_roles', weight='B') +
                    SearchVector('all_job_titles', weight='B') +
                    SearchVector('all_company_sectors', weight='B')
            )

            silver_vector = SearchVector('portfolio__bio_narrative', weight='C')

            direct_db_query = SearchQuery(direct_string, search_type='websearch') if direct_string else None
            semantic_db_query = SearchQuery(semantic_string, search_type='websearch') if semantic_string else None

            clean_query_word = direct_string.split()[0].lower() if direct_string else raw_query.split()[0].lower()

            results = scored_users.annotate(
                platinum_rank=Cast(SearchRank(platinum_vector, direct_db_query) * 1000.0,
                                   FloatField()) if direct_db_query else Value(0.0, output_field=FloatField()),

                gold_rank=Cast(SearchRank(gold_vector, direct_db_query) * 300.0,
                               FloatField()) if direct_db_query else Value(0.0, output_field=FloatField()),

                silver_rank=Cast(SearchRank(silver_vector, direct_db_query) * 50.0,
                                 FloatField()) if direct_db_query else Value(0.0, output_field=FloatField()),

                semantic_rank=Cast(
                    SearchRank(platinum_vector, semantic_db_query) * 100.0 +
                    SearchRank(gold_vector, semantic_db_query) * 50.0,
                    FloatField()
                ) if semantic_db_query else Value(0.0, output_field=FloatField()),

                regex_boost=Case(
                    When(full_name__iregex=fr'\b{clean_query_word}\b', then=Value(1000.0)),
                    When(portfolio__field_of_interest__iregex=fr'\b{clean_query_word}\b', then=Value(800.0)),
                    When(all_headlines__iregex=fr'\b{clean_query_word}\b', then=Value(800.0)),
                    default=Value(0.0),
                    output_field=FloatField()
                )

            ).annotate(
                absolute_score=ExpressionWrapper(
                    F('platinum_rank') + F('gold_rank') + F('silver_rank') + F('semantic_rank') + F('regex_boost') + F('total_quality'),
                    output_field=FloatField()
                )
            ).filter(
                Q(platinum_rank__gt=0.0) | Q(gold_rank__gt=0.0) | Q(silver_rank__gt=0.0) | Q(semantic_rank__gt=0.0) | Q(regex_boost__gt=0.0)
            ).order_by('-is_selected', '-absolute_score', '-portfolio__last_signal_update', '-date_joined')

        else:
            results = scored_users.order_by('-is_selected', '-total_quality', '-portfolio__last_signal_update')
    else:
        results = scored_users.order_by('-is_selected', '-total_quality', '-portfolio__last_signal_update')

    if role_filter and role_filter != 'ALL':
        results = results.filter(role=role_filter)

    results = results.distinct()

    # ==============================================================================
    # 🔒 EXTENDED PAYWALL LOCK: Hard limit increased to top 50 profiles
    # ==============================================================================
    results = results[:50]  # <--- UPDATED FROM 20 TO 50

    paginator = Paginator(results, 100)
    page_number = request.GET.get('page')
    try:
        people_page = paginator.get_page(page_number)
    except PageNotAnInteger:
        people_page = paginator.get_page(1)
    except EmptyPage:
        people_page = paginator.get_page(paginator.num_pages)

    unread_count = 0
    if request.user.is_authenticated:
        try:
            from workspace.models import ChatMessage
            unread_count = ChatMessage.objects.filter(receiver=request.user, is_read=False).count()
        except ImportError:
            pass

    return render(request, 'network/nexus_feed.html', {
        'people': people_page,
        'spotlight_users': spotlight_users,  # <--- PASSED TO TEMPLATE FOR THE NEW CAROUSEL UI
        'top_10_users': top_10_users,  # <--- PASSED TO TEMPLATE FOR TOP 10 SECTION
        'search_query': raw_query,
        'current_role': role_filter,
        'unread_msg_count': unread_count,
        'active_tab': 'people',
        'show_paywall': True,
    })


# ==============================================================================
# 🏢 THE COMPANY NEXUS (INTELLIGENT BUSINESS DISCOVERY)
# ==============================================================================
def company_nexus(request):
    """
    The Business Hub / Company Discovery Feed.
    Prioritizes fully completed company profiles (Logos, Covers, Services).
    Respects Admin Pinning (is_selected) and Banning (is_banned_from_nexus).
    """
    raw_query = request.GET.get('q', '').strip()
    sector_filter = request.GET.get('sector', 'ALL')
    objective_filter = request.GET.get('objective', 'ALL')

    # 1. Base Queryset & QUALITY ALGORITHM 🏆
    base_companies = Company.objects.filter(is_banned_from_nexus=False).prefetch_related(
        'services', 'members__user'
    ).annotate(
        # A. Count how many services they have built out
        service_count=Count('services', distinct=True),

        # B. Reward complete profiles with heavy points
        score_logo=Case(
            When(Q(logo='') | Q(logo__isnull=True), then=Value(0.0)),
            default=Value(20.0), output_field=FloatField()
        ),
        score_cover=Case(
            When(Q(cover_image='') | Q(cover_image__isnull=True), then=Value(0.0)),
            default=Value(15.0), output_field=FloatField()
        ),
        score_mission=Case(
            When(Q(mission_stmt='') | Q(mission_stmt__isnull=True), then=Value(0.0)),
            default=Value(10.0), output_field=FloatField()
        ),

        # C. Multiply services count by 5 points each
        score_services=Cast(F('service_count') * 5, FloatField()),

        # D. Small boost if they are actively looking to hire (shows active intent)
        score_hiring=Case(When(is_hiring=True, then=Value(10.0)), default=Value(0.0), output_field=FloatField())
    ).annotate(
        # THE ULTIMATE COMPANY QUALITY METRIC
        total_company_quality=ExpressionWrapper(
            F('score_logo') + F('score_cover') + F('score_mission') + F('score_services') + F('score_hiring'),
            output_field=FloatField()
        )
    )

    # 2. Search & Filtering Engine
    if raw_query:
        # A. Tap into the OmniIndustryOracle to mind-read the query
        (
            direct_string, semantic_string, loc_tags, skill_tags,
            min_experience, is_hiring, is_senior, is_junior
        ) = OmniIndustryOracle.process_omni_intent(raw_query)

        # B. Apply Invisible Constraints derived from NLP
        if is_hiring:
            base_companies = base_companies.filter(is_hiring=True)
        for loc in loc_tags:
            base_companies = base_companies.filter(location__icontains=loc)

        # C. Deep Search Vectors (Cross-table aggregations for products/services)
        base_companies = base_companies.annotate(
            all_services=StringAgg('services__name', delimiter=' ', distinct=True),
            all_service_desc=StringAgg('services__description', delimiter=' ', distinct=True),
        )

        business_vector = (
                SearchVector('name', weight='A') +
                SearchVector('sector', weight='A') +
                SearchVector('location', weight='B') +
                SearchVector('mission_stmt', weight='C') +
                SearchVector('all_services', weight='B') +
                SearchVector('all_service_desc', weight='D')
        )

        # Combine direct and semantic keywords for the final DB query
        combined_query_string = f"{direct_string} {semantic_string}".strip()
        final_search_string = combined_query_string if combined_query_string else raw_query

        search_query = SearchQuery(final_search_string, search_type='websearch')
        clean_query_word = raw_query.split()[0].lower() if raw_query else ''

        companies = base_companies.annotate(
            search_rank=Cast(SearchRank(business_vector, search_query) * 100.0, FloatField()),
            exact_boost=Case(
                When(name__iregex=fr'\b{clean_query_word}\b', then=Value(500.0)),
                When(sector__iregex=fr'\b{clean_query_word}\b', then=Value(200.0)),
                default=Value(0.0),
                output_field=FloatField()
            )
        ).annotate(
            # Combine Rank + Exact Matches + The Quality Metric
            total_rank=ExpressionWrapper(
                F('search_rank') + F('exact_boost') + F('total_company_quality'),
                output_field=FloatField()
            )
        ).filter(
            Q(search_rank__gt=0.01) | Q(exact_boost__gt=0.0) | Q(name__icontains=raw_query)
        ).order_by('-is_selected', '-total_rank', '-created_at')

    else:
        # Default sort: Prioritize the highest quality, most complete profiles first!
        companies = base_companies.order_by('-is_selected', '-total_company_quality', '-created_at')

    # 3. Apply Hard Filters from UI Dropdowns
    if sector_filter and sector_filter != 'ALL':
        companies = companies.filter(sector__iexact=sector_filter)
    if objective_filter and objective_filter != 'ALL':
        companies = companies.filter(looking_for=objective_filter)

    # 4. Pagination
    companies = companies.distinct()
    paginator = Paginator(companies, 48)  # 48 items per page
    page_number = request.GET.get('page')

    try:
        companies_page = paginator.get_page(page_number)
    except PageNotAnInteger:
        companies_page = paginator.get_page(1)
    except EmptyPage:
        companies_page = paginator.get_page(paginator.num_pages)

    # 5. Global Inbox Badge Context
    unread_count = 0
    if request.user.is_authenticated:
        try:
            from workspace.models import ChatMessage
            unread_count = ChatMessage.objects.filter(receiver=request.user, is_read=False).count()
        except ImportError:
            pass

    return render(request, 'network/company_nexus.html', {
        'companies': companies_page,
        'search_query': raw_query,
        'current_sector': sector_filter,
        'current_objective': objective_filter,
        'unread_msg_count': unread_count,
        'active_tab': 'teams',
    })


# ==============================================================================
# 📡 2. LIVE SIGNALS (THE GLOBAL POSTS FEED)
# ==============================================================================
def nexus_posts(request):
    """The Global Community Board for Live Posts."""
    posts = NetworkPost.objects.filter(is_active=True).select_related(
        'author__portfolio'
    ).order_by('-created_at')[:50]

    unread_count = 0
    if request.user.is_authenticated:
        try:
            from workspace.models import ChatMessage
            unread_count = ChatMessage.objects.filter(receiver=request.user, is_read=False).count()
        except ImportError:
            pass

    context = {
        'posts': posts,
        'unread_msg_count': unread_count,
    }
    return render(request, 'network/nexus_posts.html', context)


# ==============================================================================
# 🛠️ 3. NETWORK POST MANAGEMENT (CRUD)
# ==============================================================================
class NetworkPostDetailView(DetailView):
    """Deep dive page for a specific post."""
    model = NetworkPost
    template_name = 'network/signal_detail.html'
    context_object_name = 'post'

    def get_queryset(self):
        return NetworkPost.objects.filter(is_active=True).select_related(
            'author__portfolio'
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = "View Initiative"
        return ctx


class MyNetworkPostListView(LoginRequiredMixin, ListView):
    """Dashboard for a user to manage all their past posts."""
    model = NetworkPost
    template_name = 'network/my_signals.html'
    context_object_name = 'posts'

    def get_queryset(self):
        return NetworkPost.objects.filter(author=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = "My Initiatives"
        return ctx


class NetworkPostCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create a new post to broadcast to the network."""
    model = NetworkPost
    form_class = NetworkPostForm
    template_name = 'network/signal_form.html'
    success_url = reverse_lazy('nexus_feed')
    success_message = "Your initiative has been broadcasted to the Nexus!"

    def form_valid(self, form):
        form.instance.author = self.request.user
        NetworkPost.objects.filter(author=self.request.user, is_active=True).update(is_active=False)
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = "Broadcast an Initiative"
        return ctx


class NetworkPostUpdateView(LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin, UpdateView):
    """Edit an existing post."""
    model = NetworkPost
    form_class = NetworkPostForm
    template_name = 'network/signal_form.html'
    success_url = reverse_lazy('nexus_feed')
    success_message = "Your initiative has been updated."

    def test_func(self):
        return self.request.user == self.get_object().author

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = "Edit your Initiative"
        ctx['is_edit'] = True
        return ctx


class NetworkPostDeleteView(LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin, DeleteView):
    """Permanently delete a network post."""
    model = NetworkPost
    template_name = 'network/signal_confirm_delete.html'
    success_url = reverse_lazy('nexus_feed')
    success_message = "Initiative permanently removed."

    def test_func(self):
        return self.request.user == self.get_object().author


# ⚠️ Legacy view block preserved exactly as provided to prevent breakage
class NetworkPostDetailView(DetailView):
    """Deep dive page for a specific post."""
    model = NetworkPost
    template_name = 'network/signal_detail.html'
    context_object_name = 'post'

    def get_queryset(self):
        # Only active posts viewable, optimize author fetch
        return NetworkPost.objects.filter(is_active=True).select_related(
            'author__visionary_profile',
            'author__founder_profile',
            'author__expert_profile'
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = "View Initiative"
        return ctx