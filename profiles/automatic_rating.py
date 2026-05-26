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
        """Helper to scan how deeply a user wrote their narratives."""
        if not text: return 0
        length = len(str(text).strip())
        if length >= excellent_len: return 12
        if length >= good_len: return 6
        if length >= basic_len: return 2
        return 0

    @staticmethod
    def calculate_power_score(user) -> int:
        """Calculates a ruthless AI score out of 100. Impossible to cheat."""
        score = 0

        # ==========================================
        # 1. THE BASE IDENTITY MATRIX (Max 25 points)
        # ==========================================
        if getattr(user, 'avatar', None): score += 5
        if getattr(user, 'cover_image', None): score += 5
        if getattr(user, 'is_verified', False): score += 5

        # Social & Contact Grinding
        score += min(user.social_links.count() * 2, 6)  # Max 6 pts (Needs 3 Socials)
        score += min(user.contact_methods.count() * 2, 4)  # Max 4 pts (Needs 2 Contacts)

        # ==========================================
        # 2. THE FLUID PORTFOLIO MATRIX (Max 80 points)
        # ==========================================
        if hasattr(user, 'portfolio'):
            portfolio = user.portfolio

            # --- AI Reading their Text (Max 25 points) ---
            if portfolio.headlines.filter(is_primary=True).exists(): score += 3
            score += CoreLinkOracle._get_text_score(portfolio.bio_narrative, excellent_len=300, good_len=150)  # Max 12
            score += CoreLinkOracle._get_text_score(portfolio.current_mission, excellent_len=200,
                                                    good_len=100)  # Max 10

            # --- Proof of Work & Mastery Volume (Max 55 points) ---
            if getattr(portfolio, 'cv_file', None): score += 5

            # Projects (Real-world or Practice)
            score += min(portfolio.projects.count() * 5, 15)  # Needs 3 Projects for max 15

            # Work Experience
            score += min(portfolio.experiences.count() * 5, 10)  # Needs 2 Jobs for max 10

            # Verified Credentials (Degrees/Certs)
            score += min(portfolio.credentials.count() * 5, 10)  # Needs 2 Credentials for max 10

            # Skill Evolution (INTERESTED -> LEARNING -> MASTERED)
            score += min(portfolio.skills.count() * 2, 10)  # Needs 5 Skills for max 10

            # Content / Journaling Pulse
            score += min(portfolio.content_posts.count() * 2.5, 5)  # Needs 2 Posts for max 5

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

            # Deep Assets (Max 25 points)
            score += min(company.services.count() * 5, 10)  # Needs 2 Services for max 10
            score += min(company.milestones.count() * 5, 10)  # Needs 2 Milestones for max 10
            score += min(company.news_articles.count() * 2.5, 5)  # Needs 2 Articles for max 5

        return min(int(score), 100)

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