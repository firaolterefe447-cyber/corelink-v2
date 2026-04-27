"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CORELINK NETWORKING SYSTEM                              ║
║                    Professional Collaboration Platform                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

Domain: Professional Networking & Collaboration
Description: 
    Advanced networking system for connecting professionals, entrepreneurs, and 
    innovators. Features intelligent matching, project collaboration, and 
    opportunity discovery.
    
Key Features:
    • Project-based collaboration matching
    • Multi-stage project development tracking
    • Intelligent partnership requirement system
    • Real-time activity feeds
    • Professional opportunity discovery

Architecture:
    - NetworkPost: Central collaboration and project posts
    - Intelligent categorization by project type and stage
    - Need-based matching system
    - Activity tracking and engagement metrics

Author: CoreLink Development Team
Version: 2.0.0
Last Updated: 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# # SYSTEM IMPORTS & DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════════
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

# ═══════════════════════════════════════════════════════════════════════════════
# # 1. NETWORK COLLABORATION SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class NetworkPost(models.Model):
    """
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                    PROFESSIONAL COLLABORATION POST                         ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    
    Purpose: Central platform for professional collaboration and project opportunities
    
    Features:
    • Multi-dimensional project categorization
    • Intelligent matching algorithms
    • Progress tracking through development stages
    • Flexible partnership requirements
    • Real-time activity management
    
    Use Cases:
    - Startup founding team recruitment
    - Project collaboration opportunities
    - Expert advisory partnerships
    - Business development initiatives
    - Innovation challenge participation
    
    Matching Intelligence:
    - Project type compatibility
    - Development stage alignment
    - Skill requirement matching
    - Geographic preference consideration
    - Timeline synchronization
    
    Workflow Stages:
    1. Ideation: Concept development and validation
    2. Prototyping: MVP development and testing
    3. Validation: Market research and user feedback
    4. Traction: Growth and user acquisition
    5. Expansion: Scaling and market expansion
    """

    # ═══════════════════════════════════════════════════════════════════════════════
    # # PROJECT NATURE CLASSIFICATION
    # ═══════════════════════════════════════════════════════════════════════════════
    class ProjectType(models.TextChoices):
        """Classification of project scope and duration"""
        STARTUP = 'STARTUP', _('Startup / Business')
        SPECIFIC_PROJECT = 'SPECIFIC_PROJECT', _('Specific Project')

    # ═══════════════════════════════════════════════════════════════════════════════
    # # PROJECT MATURITY STAGES
    # ═══════════════════════════════════════════════════════════════════════════════
    class Stage(models.TextChoices):
        """Development stage progression for projects"""
        IDEATION = 'IDEATION', _('Ideation & Discovery')
        PROTOTYPING = 'PROTOTYPING', _('Prototyping & Build')
        VALIDATION = 'VALIDATION', _('Market Validation')
        TRACTION = 'TRACTION', _('Early Traction')
        EXPANSION = 'EXPANSION', _('Scale & Expansion')

    # ═══════════════════════════════════════════════════════════════════════════════
    # # PARTNERSHIP REQUIREMENTS
    # ═══════════════════════════════════════════════════════════════════════════════
    class Need(models.TextChoices):
        """Types of collaboration and partnership sought"""
        COFOUNDER = 'COFOUNDER', _('Co-Founder')
        COLLABORATOR = 'COLLABORATOR', _('Project Collaborator')
        TEAM = 'TEAM', _('Team Member')
        ADVISOR = 'ADVISOR', _('Advisor / Mentor')
        FEEDBACK = 'FEEDBACK', _('Feedback & Testing')

    # ═══════════════════════════════════════════════════════════════════════════════
    # # SYSTEM IDENTITY & OWNERSHIP
    # ═══════════════════════════════════════════════════════════════════════════════
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='network_posts',
        help_text=_("Project author and primary contact")
    )

    # ═══════════════════════════════════════════════════════════════════════════════
    # # PART 1: THE INITIATIVE (What I am doing)
    # ═══════════════════════════════════════════════════════════════════════════════
    headline = models.CharField(
        max_length=1500,
        help_text=_("A concise, professional title for the collaboration opportunity")
    )
    description = models.TextField(
        help_text=_("Detailed overview of the project objectives, vision, and roadmap")
    )
    project_type = models.CharField(
        max_length=20,
        choices=ProjectType.choices,
        default=ProjectType.STARTUP,
        help_text=_("Nature and scope of the project")
    )
    project_stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.IDEATION,
        help_text=_("Current development stage of the project")
    )

    # ═══════════════════════════════════════════════════════════════════════════════
    # # PART 2: THE REQUIREMENT (What I am looking for)
    # ═══════════════════════════════════════════════════════════════════════════════
    need_type = models.CharField(
        max_length=20,
        choices=Need.choices,
        default=Need.COLLABORATOR,
        help_text=_("Type of partnership or collaboration sought")
    )
    looking_for = models.TextField(
        help_text=_("Detailed description of expertise, commitment, and background required")
    )

    # ═══════════════════════════════════════════════════════════════════════════════
    # # PART 3: STATUS & METADATA
    # ═══════════════════════════════════════════════════════════════════════════════
    is_active = models.BooleanField(
        default=True,
        help_text=_("Controls visibility in the network feed")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Network Post"
        verbose_name_plural = "Network Posts"
        indexes = [
            models.Index(fields=['project_type', 'need_type', 'project_stage', 'is_active']),
            models.Index(fields=['author', 'created_at']),
            models.Index(fields=['is_active', 'created_at']),
            models.Index(fields=['project_stage', 'need_type']),
        ]

    def __str__(self):
        """Human-readable representation with project context"""
        return f"[{self.get_project_type_display()}] {self.headline}"

    # ═══════════════════════════════════════════════════════════════════════════════
    # # INTELLIGENT MATCHING HELPERS
    # ═══════════════════════════════════════════════════════════════════════════════
    def get_compatibility_score(self, user_profile):
        """
        Calculate compatibility score with a user profile.
        
        Args:
            user_profile: User profile to match against
            
        Returns:
            float: Compatibility score (0-100)
        """
        # This would be implemented with actual matching logic
        # Based on skills, experience, location preferences, etc.
        return 75.0  # Placeholder implementation

    def is_stage_compatible(self, preferred_stages):
        """
        Check if project stage matches user preferences.
        
        Args:
            preferred_stages (list): List of preferred stages
            
        Returns:
            bool: Compatibility status
        """
        return self.project_stage in preferred_stages

    def get_matching_summary(self):
        """
        Generate a summary for matching algorithms.
        
        Returns:
            dict: Key attributes for matching
        """
        return {
            'project_type': self.project_type,
            'stage': self.project_stage,
            'need_type': self.need_type,
            'keywords': self.headline.lower().split() + self.description.lower().split()
        }

    # ═══════════════════════════════════════════════════════════════════════════════
    # # WORKFLOW MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════════
    def advance_stage(self):
        """Advance project to the next development stage"""
        stage_order = [stage[0] for stage in self.Stage.choices]
        current_index = stage_order.index(self.project_stage)
        
        if current_index < len(stage_order) - 1:
            self.project_stage = stage_order[current_index + 1]
            self.save()
            return True
        return False

    def archive(self):
        """Archive the post and remove from active feed"""
        self.is_active = False
        self.save()

    def reactivate(self):
        """Reactivate an archived post"""
        self.is_active = True
        self.save()

    @property
    def is_recruiting(self):
        """Check if the post is actively seeking collaborators"""
        return self.is_active and self.need_type != self.Need.FEEDBACK

    @property
    def urgency_level(self):
        """
        Determine urgency based on project stage.
        
        Returns:
            str: Urgency level (High, Medium, Low)
        """
        early_stages = [self.Stage.IDEATION, self.Stage.PROTOTYPING]
        if self.project_stage in early_stages:
            return "High"
        elif self.project_stage == self.Stage.VALIDATION:
            return "Medium"
        else:
            return "Low"

    def get_absolute_url(self):
        """Generate the absolute URL for this post"""
        from django.urls import reverse
        return reverse('network_post_detail', kwargs={'pk': self.pk})
