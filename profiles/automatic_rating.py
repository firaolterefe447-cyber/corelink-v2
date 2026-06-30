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
    def _get_text_score(text: str, excellent_len=300, good_len=150, basic_len=50) -> int:
        """Helper to scan how deeply a user wrote their narratives - SMOOTHED GRADIENT."""
        if not text: return 0
        length = len(str(text).strip())
        if length >= excellent_len: return 4  # Reduced from 12
        if length >= good_len: return 2  # Reduced from 6
        if length >= basic_len: return 1  # Reduced from 2
        return 0

    @staticmethod
    def calculate_power_score(user) -> int:
        """
        REFINED ORACLE SCORING ENGINE
        Smoothly rewards deliberate, high-quality profile building.
        Progression is gradual - requires sustained effort to advance.
        Cap at 98 - Admin manually grants 100 for exceptional cases.
        """
        score = 0

        # ==========================================
        # 1. THE BASE IDENTITY MATRIX (Max 9 points)
        # ==========================================
        if getattr(user, 'avatar', None): score += 2  # Reduced from 5
        if getattr(user, 'cover_image', None): score += 2  # Reduced from 5
        # Verification removed - all users are verified

        # Social & Contact - REWARDS SINGLE ENTRIES (SMOOTHED)
        score += min(user.social_links.count() * 1, 3)  # Max 3 pts (was 6)
        score += min(user.contact_methods.count() * 1, 2)  # Max 2 pts (was 4)

        # ==========================================
        # 2. THE FLUID PORTFOLIO MATRIX (Max ~55 points)
        # ==========================================
        if hasattr(user, 'portfolio'):
            portfolio = user.portfolio

            # --- AI Reading their Text (Max 9 points - SMOOTHED) ---
            if portfolio.headlines.filter(is_primary=True).exists(): score += 1  # Reduced from 3
            score += CoreLinkOracle._get_text_score(portfolio.bio_narrative, excellent_len=300, good_len=150)  # Max 4 (was 12)
            score += CoreLinkOracle._get_text_score(portfolio.current_mission, excellent_len=200,
                                                    good_len=100)  # Max 4 (was 8)

            # --- Proof of Work & Mastery Volume (SMOOTHED REWARDS) ---
            if getattr(portfolio, 'cv_file', None): score += 2  # Reduced from 5

            # Projects - SMOOTHED WITH GALLERY BONUS
            for project in portfolio.projects.all():
                # Base project points (reduced)
                score += 2  # Each project worth 2 points (was 6-25)
                
                # Gallery bonus - rewards visual evidence
                gallery_count = project.gallery.count()
                if gallery_count >= 5:
                    score += 5  # Elite: 5+ images/PDFs
                elif gallery_count >= 3:
                    score += 3  # Strong: 3-4 images/PDFs
                elif gallery_count >= 1:
                    score += 1  # Base: 1-2 images/PDFs

            # Work Experience - SMOOTHED CAREER DEPTH
            exp_count = portfolio.experiences.count()
            if exp_count >= 5:
                score += 5  # Elite: 5+ jobs (was 15)
            elif exp_count >= 3:
                score += 3  # Strong: 3-4 jobs (was 10)
            elif exp_count >= 1:
                score += 1  # Base: 1-2 jobs (was 5)

            # Credentials - SMOOTHED EXPERTISE REWARDS
            cred_count = portfolio.credentials.count()
            if cred_count >= 5:
                score += 5  # Elite: 5+ credentials (was 15)
            elif cred_count >= 3:
                score += 3  # Strong: 3-4 credentials (was 10)
            elif cred_count >= 1:
                score += 1  # Base: 1-2 credentials (was 5)

            # Skills - SMOOTHED WITH CONTEXT BONUS
            for skill in portfolio.skills.all():
                # Base skill point (reduced)
                score += 1  # Each skill worth 1 point (was 3-15)
                
                # Context bonus - rewards detailed explanations
                if skill.context and len(skill.context.strip()) >= 50:
                    score += 1  # Bonus for meaningful context

            # Languages - SMOOTHED MULTILINGUAL REWARDS
            language_count = portfolio.languages.count()
            if language_count >= 5:
                score += 3  # Elite: 5+ languages (was 10)
            elif language_count >= 3:
                score += 2  # Strong: 3-4 languages (was 7)
            elif language_count >= 1:
                score += 1  # Base: 1-2 languages (was 3)

            # Content / Journaling - SMOOTHED OUTPUT REWARDS
            content_count = portfolio.content_posts.count()
            if content_count >= 10:
                score += 4  # Elite: 10+ posts (was 10)
            elif content_count >= 5:
                score += 2  # Strong: 5-9 posts (was 6)
            elif content_count >= 1:
                score += 1  # Base: 1-4 posts (was 3)

        # ==========================================
        # 3. CORPORATE ASSET OVERRIDE (Bonus ~20 points - SMOOTHED)
        # ==========================================
        # If the user is building a company, they get alternate ways to gain points.
        membership = user.company_memberships.filter(is_active=True).select_related('company').first()
        if membership and membership.company:
            company = membership.company

            # Visuals & Metadata (Max 6 points - reduced)
            if getattr(company, 'logo', None): score += 2  # Reduced from 5
            if getattr(company, 'cover_image', None): score += 2  # Reduced from 5
            if getattr(company, 'mission_stmt', None): score += 2  # Reduced from 5

            # Deep Assets - SMOOTHED REWARDS
            service_count = company.services.count()
            if service_count >= 5:
                score += 5  # Elite: 5+ services (was 15)
            elif service_count >= 2:
                score += 2  # Base: 2-4 services (was 8)

            milestone_count = company.milestones.count()
            if milestone_count >= 5:
                score += 5  # Elite: 5+ milestones (was 15)
            elif milestone_count >= 2:
                score += 2  # Base: 2-4 milestones (was 8)

            news_count = company.news_articles.count()
            if news_count >= 5:
                score += 3  # Elite: 5+ articles (was 10)
            elif news_count >= 2:
                score += 1  # Base: 2-4 articles (was 5)

        return min(int(score), 98)

    @staticmethod
    def map_score_to_rating(score: int) -> int:
        """SMOOTHED RATING CONVERSION - More gradual progression"""
        if score >= 60: return 4  # Elite (Requires sustained, deliberate effort)
        if score >= 40: return 3  # Solid Pro (Consistent profile building)
        if score >= 25: return 2  # Developing (Meaningful engagement)
        if score >= 10: return 1  # Basic (Initial profile setup)
        return 0  # Ghost (Empty or minimal)

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
                'portfolio__projects__gallery',
                'portfolio__experiences',
                'portfolio__credentials',
                'portfolio__skills',
                'portfolio__languages',
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

            # 2. APPLY ORACLE'S STAR RATING (NO LOCKS - EVERY UPDATE COUNTS)
            if portfolio.admin_rating != calculated_rating:
                old_rating = portfolio.admin_rating
                old_score = getattr(portfolio, 'oracle_score', 0)
                portfolio.admin_rating = calculated_rating
                update_fields.append('admin_rating')
                needs_save = True

                if calculated_rating > old_rating:
                    print(
                        f"[ORACLE PROMOTION] Elevated {user.full_name} from {old_rating} to {calculated_rating} Stars! (Score: {old_score} → {power_score})")
                elif calculated_rating < old_rating:
                    print(
                        f"[ORACLE DEMOTION] Downgraded {user.full_name} from {old_rating} to {calculated_rating} Stars. (Score: {old_score} → {power_score})")
                else:
                    print(
                        f"[ORACLE UPDATE] {user.full_name} maintained {calculated_rating} Stars. (Score: {old_score} → {power_score})")
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