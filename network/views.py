# ==============================================================================
# 🚀 PURE CORE ENGINE IMPORTS (NO EXTENSIONS REQUIRED)
# ==============================================================================
import re
import difflib
import operator
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
    Q, F, Case, When, Value, IntegerField, FloatField, Max, ExpressionWrapper, Prefetch
)
from django.db.models.functions import Coalesce, Greatest, Cast, Now, ExtractDay

# Standard Postgres Full-Text Search (No pg_trgm needed, perfectly cPanel safe)
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.aggregates import StringAgg

# Local App Imports
from .models import NetworkPost
from .forms import NetworkPostForm

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

    # 🛡️ 1. BASE SHIELD (Fluid Architecture Transition)
    # Using 'portfolio' relation explicitly. Exclude internal Admin roles.
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

    # 💎 2b. TEMPORAL GRAVITY (Freshness & Quality Metrics)
    scored_users = base_users.annotate(
        score_avatar=Case(When(avatar='', then=0), default=20, output_field=FloatField()),
        score_verified=Case(When(is_verified=True, then=15), default=0, output_field=FloatField()),

        days_inactive=days_inactive_expr,
        freshness_boost=Greatest(Value(0.0), Value(15.0) - Cast(F('days_inactive'), FloatField()) / 2.0),

        # Fluid Rating System
        admin_score=Cast(Coalesce('portfolio__admin_rating', Value(0)) * 10, FloatField())
    ).annotate(
        total_quality=F('score_avatar') + F('score_verified') + F('admin_score') + F('freshness_boost')
    )

    if raw_query:
        # 🧠 3. AWAKEN THE OMNI-INDUSTRY ORACLE
        (
            direct_string,
            semantic_string,
            loc_tags, skill_tags,
            min_experience, is_hiring, is_senior, is_junior
        ) = OmniIndustryOracle.process_omni_intent(raw_query)

        # --- APPLY INVISIBLE HR CONSTRAINTS (FLUID BLOCK ADAPTATION) ---
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
                # Fluid Sub-Block Aggregations
                all_skills=StringAgg('portfolio__skills__name', delimiter=' ', distinct=True),
                all_headlines=StringAgg('portfolio__headlines__title', delimiter=' ', distinct=True),
                all_exp_roles=StringAgg('portfolio__experiences__role_title', delimiter=' ', distinct=True),

                # Company Legacy fallback
                all_job_titles=StringAgg('company_memberships__job_title', delimiter=' ', distinct=True),
                all_company_sectors=StringAgg('company_memberships__company__sector', delimiter=' ', distinct=True),
            )

            # 👑 THE PLATINUM VECTOR (Titles, Current Focus, Headlines)
            platinum_vector = (
                    SearchVector('portfolio__current_mission', weight='A') +
                    SearchVector('portfolio__field_of_interest', weight='A') +
                    SearchVector('all_headlines', weight='A')
            )

            # 🥇 THE GOLD VECTOR (Skills, Roles, Sectors)
            gold_vector = (
                    SearchVector('all_skills', weight='A') +
                    SearchVector('all_exp_roles', weight='B') +
                    SearchVector('all_job_titles', weight='B') +
                    SearchVector('all_company_sectors', weight='B')
            )

            # 🥈 THE SILVER VECTOR (Biographies, Long Text)
            silver_vector = SearchVector('portfolio__bio_narrative', weight='C')

            direct_db_query = SearchQuery(direct_string, search_type='websearch') if direct_string else None
            semantic_db_query = SearchQuery(semantic_string, search_type='websearch') if semantic_string else None

            # Base word for Regex Fallback
            clean_query_word = direct_string.split()[0].lower() if direct_string else raw_query.split()[0].lower()

            results = scored_users.annotate(

                # 👑 PLATINUM SCORE (Multiplier x1000)
                platinum_rank=Cast(SearchRank(platinum_vector, direct_db_query) * 1000.0,
                                   FloatField()) if direct_db_query else Value(0.0, output_field=FloatField()),

                # 🥇 GOLD SCORE (Multiplier x300)
                gold_rank=Cast(SearchRank(gold_vector, direct_db_query) * 300.0,
                               FloatField()) if direct_db_query else Value(0.0, output_field=FloatField()),

                # 🥈 SILVER SCORE (Multiplier x50)
                silver_rank=Cast(SearchRank(silver_vector, direct_db_query) * 50.0,
                                 FloatField()) if direct_db_query else Value(0.0, output_field=FloatField()),

                # 🌌 SEMANTIC NETWORK SCORE (Multiplier x100)
                semantic_rank=Cast(
                    SearchRank(platinum_vector, semantic_db_query) * 100.0 +
                    SearchRank(gold_vector, semantic_db_query) * 50.0,
                    FloatField()
                ) if semantic_db_query else Value(0.0, output_field=FloatField()),

                # 🎯 EXACT REGEX BOOST (The Ultimate Guarantee)
                regex_boost=Case(
                    When(full_name__iregex=fr'\b{clean_query_word}\b', then=Value(1000.0)),
                    When(portfolio__field_of_interest__iregex=fr'\b{clean_query_word}\b', then=Value(800.0)),
                    When(all_headlines__iregex=fr'\b{clean_query_word}\b', then=Value(800.0)),
                    default=Value(0.0),
                    output_field=FloatField()
                )

            ).annotate(
                # THE ABSOLUTE MASTER FORMULA
                absolute_score=ExpressionWrapper(
                    F('platinum_rank') +
                    F('gold_rank') +
                    F('silver_rank') +
                    F('semantic_rank') +
                    F('regex_boost') +
                    F('total_quality'),
                    output_field=FloatField()
                )
            ).filter(
                # Ensure they actually matched the search conceptually
                Q(platinum_rank__gt=0.0) |
                Q(gold_rank__gt=0.0) |
                Q(silver_rank__gt=0.0) |
                Q(semantic_rank__gt=0.0) |
                Q(regex_boost__gt=0.0)
            ).order_by('-is_selected', '-absolute_score', '-portfolio__last_signal_update', '-date_joined')

        else:
            results = scored_users.order_by('-is_selected', '-total_quality', '-portfolio__last_signal_update')
    else:
        results = scored_users.order_by('-is_selected', '-total_quality', '-portfolio__last_signal_update')

    # 🧹 5. CLEANUP & HIGH-SPEED PAGINATION
    if role_filter and role_filter != 'ALL':
        results = results.filter(role=role_filter)

    results = results.distinct()

    paginator = Paginator(results, 1000)
    page_number = request.GET.get('page')
    try:
        people_page = paginator.get_page(page_number)
    except PageNotAnInteger:
        people_page = paginator.get_page(1)
    except EmptyPage:
        people_page = paginator.get_page(paginator.num_pages)

    # 📬 INBOX BADGE
    unread_count = 0
    if request.user.is_authenticated:
        try:
            from workspace.models import ChatMessage
            unread_count = ChatMessage.objects.filter(receiver=request.user, is_read=False).count()
        except ImportError:
            pass

    return render(request, 'network/nexus_feed.html', {
        'people': people_page,
        'search_query': raw_query,
        'current_role': role_filter,
        'unread_msg_count': unread_count,
        'active_tab': 'people',
    })


# ==============================================================================
# 📡 2. LIVE SIGNALS (THE GLOBAL POSTS FEED)
# ==============================================================================
def nexus_posts(request):
    """The Global Community Board for Live Posts."""
    # Highly optimized query fetching authors and their UNIFIED PORTFOLIO
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
        # Fetch with Unified Profile logic
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
        # Optional: Auto-archive user's older posts to keep feed clean
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

