import logging
import re
from django.db import transaction
from django.contrib.auth import get_user_model
from profiles.models.new_unified_profile import UserProfile

logger = logging.getLogger(__name__)
User = get_user_model()


class CoreLinkOracle:
    """
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                 THE STRICT AUTONOMOUS RATING ENGINE (ORACLE)                 ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    """

    @staticmethod
    def _get_text_score(text: str) -> int:
        """
        HIGH-IQ TEXT SCANNER:
        Checks for unique word count instead of raw length to prevent spam (e.g., "a a a a").
        """
        if not text: return 0
        
        # Strip markdown/html and count unique meaningful words
        clean_text = re.sub(r'[^a-zA-Z0-9\s]', '', str(text).lower())
        unique_words = set(clean_text.split())
        word_count = len(unique_words)

        if word_count >= 60: return 4  # Deep, thoughtful narrative
        if word_count >= 30: return 2  # Good explanation
        if word_count >= 10: return 1  # Basic sentence
        return 0

    @staticmethod
    def calculate_power_score(user) -> int:
        score = 0

        # ==========================================
        # 1. THE BASE IDENTITY MATRIX (Max 9 points)
        # ==========================================
        if getattr(user, 'avatar', None): score += 2
        if getattr(user, 'cover_image', None): score += 2
        
        # Use len(.all()) to utilize prefetch cache (NO DB HITS)
        socials_count = len(user.social_links.all())
        contacts_count = len(user.contact_methods.all())
        score += min(socials_count * 1, 3) 
        score += min(contacts_count * 1, 2)

        # ==========================================
        # 2. THE FLUID PORTFOLIO MATRIX
        # ==========================================
        if hasattr(user, 'portfolio'):
            portfolio = user.portfolio

            # --- AI Reading (Max 9 points) ---
            primary_headlines = [h for h in portfolio.headlines.all() if h.is_primary]
            if primary_headlines: score += 1
            score += CoreLinkOracle._get_text_score(portfolio.bio_narrative)
            score += CoreLinkOracle._get_text_score(portfolio.current_mission)
            if getattr(portfolio, 'cv_file', None): score += 2

            # --- Projects (Cap: 25 points to prevent spam) ---
            project_score = 0
            for project in portfolio.projects.all():
                project_score += 2
                
                # Use len(.all()) to prevent N+1 Query explosion
                gallery_count = len(project.gallery.all())
                if gallery_count >= 5: project_score += 5
                elif gallery_count >= 3: project_score += 3
                elif gallery_count >= 1: project_score += 1
                
                # Check meta depth
                if project.main_description and len(project.main_description) > 50:
                    project_score += 1
                    
            score += min(project_score, 25) # Cap max project points

            # --- Work Experience (Cap: 15 points) ---
            exp_count = len(portfolio.experiences.all())
            if exp_count >= 5: score += 5
            elif exp_count >= 3: score += 3
            elif exp_count >= 1: score += 1

            # --- Credentials (Cap: 10 points) ---
            cred_count = len(portfolio.credentials.all())
            if cred_count >= 4: score += 5
            elif cred_count >= 2: score += 3
            elif cred_count >= 1: score += 1

            # --- Skills (Cap: 15 points) ---
            skill_score = 0
            for skill in portfolio.skills.all():
                skill_score += 1
                if skill.context and len(skill.context.strip()) >= 30:
                    skill_score += 1
            score += min(skill_score, 15) # Stop rewarding after ~7-10 good skills

            # --- Languages (Cap: 5 points) ---
            lang_count = len(portfolio.languages.all())
            if lang_count >= 3: score += 3
            elif lang_count >= 1: score += 1

            # --- Content / Journaling (Cap: 12 points) ---
            content_count = len(portfolio.content_posts.all())
            if content_count >= 10: score += 6
            elif content_count >= 5: score += 3
            elif content_count >= 1: score += 1

            # --- Services (Cap: 15 points) ---
            service_score = 0
            for service in portfolio.services.all():
                service_score += 1
                # Use len(.all()) to prevent N+1 Query explosion
                gallery_count = len(service.gallery.all())
                if gallery_count >= 3: service_score += 2
                elif gallery_count >= 1: service_score += 1
                
                # Check description depth
                if service.description and len(service.description) > 50:
                    service_score += 1
                    
                # Bonus for active services
                if service.is_active:
                    service_score += 1
                    
            score += min(service_score, 15) # Cap max service points

        # ==========================================
        # 3. CORPORATE ASSET OVERRIDE
        # ==========================================
        # Look in the prefetched list, no DB hit
        memberships = [m for m in user.company_memberships.all() if m.is_active]
        if memberships and memberships[0].company:
            company = memberships[0].company
            comp_score = 0

            if getattr(company, 'logo', None): comp_score += 2
            if getattr(company, 'cover_image', None): comp_score += 2
            if getattr(company, 'mission_stmt', None): comp_score += 2

            # Assume these are not prefetched to save global memory, so count() is ok here, 
            # OR better yet, cap the corporate bonus entirely.
            if company.services.exists(): comp_score += 3
            if company.milestones.exists(): comp_score += 3
            if company.news_articles.exists(): comp_score += 2
            
            score += min(comp_score, 15)

        # Cap absolutely at 98. (100 is manual admin override)
        return min(int(score), 98)

    @staticmethod
    def map_score_to_rating(score: int) -> int:
        if score >= 75: return 4  # Elite
        if score >= 45: return 3  # Solid Pro
        if score >= 20: return 2  # Developing
        if score >= 5:  return 1  # Basic
        return 0

    @classmethod
    def update_user_rating(cls, user_id):
        try:
            # Prefetch perfectly to eliminate N+1 queries
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
                'portfolio__content_posts',
                'portfolio__services__gallery'
            ).get(id=user_id)

            if not hasattr(user, 'portfolio'):
                return

            portfolio = user.portfolio
            power_score = cls.calculate_power_score(user)
            calculated_rating = cls.map_score_to_rating(power_score)

            # --- THE MAGIC FIX: UPDATE INSTEAD OF SAVE ---
            # By using .update(), we BYPASS the post_save signal.
            # This completely eliminates the infinite loop crash.
            if portfolio.oracle_score != power_score or portfolio.admin_rating != calculated_rating:
                
                logger.info(f"[ORACLE] Updated {user.username}: Score {portfolio.oracle_score}->{power_score}, Stars {portfolio.admin_rating}->{calculated_rating}")
                
                UserProfile.objects.filter(pk=portfolio.pk).update(
                    oracle_score=power_score,
                    admin_rating=calculated_rating
                )

        except User.DoesNotExist:
            logger.error(f"[ORACLE FATAL] Target user {user_id} does not exist.")
        except Exception as e:
            logger.error(f"[ORACLE SYSTEM FAILURE] Engine crashed on User {user_id}: {str(e)}", exc_info=True)