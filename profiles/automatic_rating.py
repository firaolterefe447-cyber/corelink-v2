import logging
from django.db import transaction
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class CoreLinkOracle:
    """
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                 THE STRICT AUTONOMOUS RATING ENGINE (ORACLE)                 ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    This engine evaluates the DEPTH and VOLUME of a user's Fluid Architecture.
    It doesn't care what "Role" the user selected; it only respects Proof of Work.
    """

    @staticmethod
    def _get_text_score(text: str, excellent_len=300, good_len=100, basic_len=50) -> int:
        """Helper to scan how deeply a user wrote their narratives - NOW MORE GRANULAR."""
        if not text: return 0
        length = len(str(text).strip())
        if length >= excellent_len: return 12
        if length >= good_len: return 6
        if length >= basic_len: return 2
        if length >= 10: return 1  # Reward even small attempts
        return 0

    @staticmethod
    def calculate_power_score(user) -> int:
        """
        ULTRA-INTELLIGENT ORACLE SCORING ENGINE
        Aggressively rewards high-achievers with massive portfolios, skills, and projects.
        Cap at 98 - Admin manually grants 100 for exceptional cases.
        """
        score = 0

        # ==========================================
        # 1. THE BASE IDENTITY MATRIX (Max 20 points)
        # ==========================================
        if getattr(user, 'avatar', None): score += 5
        if getattr(user, 'cover_image', None): score += 5
        if getattr(user, 'is_verified', False): score += 5

        # Social & Contact - REWARDS SINGLE ENTRIES
        score += min(user.social_links.count() * 2, 6)  # Max 6 pts (3 pts per social)
        score += min(user.contact_methods.count() * 2, 4)  # Max 4 pts (2 pts per contact)

        # ==========================================
        # 2. THE FLUID PORTFOLIO MATRIX (Max 78 points)
        # ==========================================
        if hasattr(user, 'portfolio'):
            portfolio = user.portfolio

            # --- AI Reading their Text (Max 23 points) ---
            if portfolio.headlines.filter(is_primary=True).exists(): score += 3
            score += CoreLinkOracle._get_text_score(portfolio.bio_narrative, excellent_len=300, good_len=150)  # Max 12
            score += CoreLinkOracle._get_text_score(portfolio.current_mission, excellent_len=200,
                                                    good_len=100)  # Max 8

            # --- Proof of Work & Mastery Volume (AGGRESSIVE REWARDS) ---
            if getattr(portfolio, 'cv_file', None): score += 5

            # Projects - MASSIVE REWARD FOR HIGH VOLUME
            project_count = portfolio.projects.count()
            if project_count >= 10:
                score += 25  # Elite: 10+ projects
            elif project_count >= 5:
                score += 18  # Strong: 5-9 projects
            elif project_count >= 3:
                score += 12  # Solid: 3-4 projects
            elif project_count >= 1:
                score += 6   # Base: 1-2 projects

            # Work Experience - REWARDS CAREER DEPTH
            exp_count = portfolio.experiences.count()
            if exp_count >= 5:
                score += 15  # Elite: 5+ jobs
            elif exp_count >= 3:
                score += 10  # Strong: 3-4 jobs
            elif exp_count >= 1:
                score += 5   # Base: 1-2 jobs

            # Credentials - REWARDS VERIFIED EXPERTISE
            cred_count = portfolio.credentials.count()
            if cred_count >= 5:
                score += 15  # Elite: 5+ credentials
            elif cred_count >= 3:
                score += 10  # Strong: 3-4 credentials
            elif cred_count >= 1:
                score += 5   # Base: 1-2 credentials

            # Skills - MASSIVE REWARD FOR SKILL DIVERSITY
            skill_count = portfolio.skills.count()
            if skill_count >= 15:
                score += 15  # Elite: 15+ skills
            elif skill_count >= 10:
                score += 12  # Strong: 10-14 skills
            elif skill_count >= 5:
                score += 8   # Solid: 5-9 skills
            elif skill_count >= 1:
                score += 3   # Base: 1-4 skills

            # Content / Journaling - REWARDS CONSISTENT OUTPUT
            content_count = portfolio.content_posts.count()
            if content_count >= 10:
                score += 10  # Elite: 10+ posts
            elif content_count >= 5:
                score += 6   # Strong: 5-9 posts
            elif content_count >= 1:
                score += 3   # Base: 1-4 posts

        # ==========================================
        # 3. CORPORATE ASSET OVERRIDE (Bonus 40 points)
        # ==========================================
        # If the user is building a company, they get alternate ways to gain points.
        membership = user.company_memberships.filter(is_active=True).select_related('company').first()
        if membership and membership.company:
            company = membership.company

            # Visuals & Metadata (Max 15)
            if getattr(company, 'logo', None): score += 5
            if getattr(company, 'cover_image', None): score += 5
            if getattr(company, 'mission_stmt', None): score += 5

            # Deep Assets - AGGRESSIVE REWARDS
            service_count = company.services.count()
            if service_count >= 5:
                score += 15  # Elite: 5+ services
            elif service_count >= 2:
                score += 8   # Base: 2-4 services

            milestone_count = company.milestones.count()
            if milestone_count >= 5:
                score += 15  # Elite: 5+ milestones
            elif milestone_count >= 2:
                score += 8   # Base: 2-4 milestones

            news_count = company.news_articles.count()
            if news_count >= 5:
                score += 10  # Elite: 5+ articles
            elif news_count >= 2:
                score += 5   # Base: 2-4 articles

        return min(int(score), 98)

    @staticmethod
    def map_score_to_rating(score: int) -> int:
        """RUTHLESS RATING CONVERSION"""
        if score >= 90: return 4  # Elite (Massive proof of work or corporate assets)
        if score >= 70: return 3  # Solid Pro (Good bios, 3+ items attached)
        if score >= 45: return 2  # Developing (Some effort, maybe 1-2 projects)
        if score >= 20: return 1  # Lazy (Avatar + 1 basic item)
        return 0  # Ghost (Empty)

    @classmethod
    def update_user_rating(cls, user_id):
        """The Master Executor: Scans, judges, and executes the rating dynamically."""
        try:
            # High-Performance DB Hit grabbing all Fluid Block counts in memory
            user = User.objects.prefetch_related(
                'social_links',
                'contact_methods',
                'company_memberships__company',
                'portfolio__headlines',
                'portfolio__projects',
                'portfolio__experiences',
                'portfolio__credentials',
                'portfolio__skills',
                'portfolio__content_posts'
            ).get(id=user_id)

            if not hasattr(user, 'portfolio'):
                print(f"[ORACLE WARNING] Ghost entity. User {user.full_name} lacks a unified Portfolio.")
                return

            portfolio = user.portfolio
            power_score = cls.calculate_power_score(user)
            calculated_rating = cls.map_score_to_rating(power_score)

            update_fields = []
            needs_save = False

            # 1. ALWAYS UPDATE RAW SCORE (For Feed Granularity)
            if getattr(portfolio, 'oracle_score', None) != power_score:
                portfolio.oracle_score = power_score
                update_fields.append('oracle_score')
                needs_save = True

            # 2. CHECK ADMIN OVERRIDES FOR STAR RATING
            is_locked = getattr(portfolio, 'is_rating_locked', False)
            is_divine = portfolio.admin_rating == 5

            if is_locked or is_divine:
                print(
                    f"[ORACLE RESTRICTED] {user.full_name}: Star Rating locked by Admin. However, raw AI score updated to {power_score}/100.")
            else:
                # Apply Oracle's star judgment if it changed
                if portfolio.admin_rating != calculated_rating:
                    old_rating = portfolio.admin_rating
                    portfolio.admin_rating = calculated_rating
                    update_fields.append('admin_rating')
                    needs_save = True

                    if calculated_rating > old_rating:
                        print(
                            f"[ORACLE PROMOTION] Elevated {user.full_name} from {old_rating} to {calculated_rating} Stars! (Score: {power_score})")
                    else:
                        print(
                            f"[ORACLE DEMOTION] Downgraded {user.full_name} from {old_rating} to {calculated_rating} Stars. (Score: {power_score})")
                else:
                    print(
                        f"[ORACLE VERDICT] {user.full_name} maintained {calculated_rating} Stars. (Score: {power_score})")

            # 3. COMMIT TO DATABASE
            if needs_save:
                portfolio.save(update_fields=update_fields)

        except User.DoesNotExist:
            print(f"[ORACLE FATAL] Target user {user_id} does not exist.")
        except Exception as e:
            logger.error(f"[ORACLE SYSTEM FAILURE] Engine crashed on User {user_id}: {str(e)}")
            print(f"[ORACLE SYSTEM FAILURE] Engine crashed on User {user_id}: {str(e)}")