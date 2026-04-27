import logging
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

# ==========================================
# IMPORT OLD LEGACY MODELS
# ==========================================
from profiles.models.expert import (
    ExpertProfile,
    ExpertHeadline,
    ExpertSkill,
    ExpertCredential,
    ExpertProject,
    ProjectGalleryImage as ExpertGalleryImage,
    ExpertExperience,
    JobPreference as OldJobPreference,
    ExpertThought
)
from profiles.models.visionary import (
    VisionaryProfile,
    Certification,
    Project as VisionaryProject,
    ProjectImage as VisionaryProjectImage,
    GrowthLog,
    LearningTarget,
    VisionBlock
)
from profiles.models.founder import (
    FounderProfile
)

# ==========================================
# IMPORT NEW UNIFIED MODELS
# ==========================================
from profiles.models.new_unified_profile import (
    UserProfile,
    ProfileHeadline,
    Skill,
    Credential,
    PortfolioProject,
    ProjectGallery,
    WorkExperience,
    ContentPost,
    UnifiedJobPreference as NewJobPreference,
    LiveOpportunity
)

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Robustly migrates legacy profiles to the Unified UserProfile system with historical timestamp preservation."

    def preserve_timestamps(self, model_class, instance_id, created_at, updated_at=None):
        """
        Bypasses Django's auto_now_add/auto_now by running a direct SQL UPDATE.
        Ensures old posts/profiles keep their original historical dates.
        """
        if not created_at:
            return

        if not updated_at:
            updated_at = created_at

        model_class.objects.filter(pk=instance_id).update(
            created_at=created_at,
            updated_at=updated_at
        )

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Starting Unified Profile Migration..."))

        # We use .count() for the total, but .iterator() so we don't load all users into RAM at once.
        total_users = User.objects.count()
        users = User.objects.all().iterator()

        success_count = 0
        error_count = 0

        for index, user in enumerate(users, 1):
            try:
                with transaction.atomic():
                    # 1. Skip if already migrated (Idempotency ensures we can run this multiple times safely)
                    if UserProfile.objects.filter(user=user).exists():
                        continue

                    # 2. Extract legacy profiles
                    expert = getattr(user, 'expert_profile', None)
                    visionary = getattr(user, 'visionary_profile', None)
                    founder = getattr(user, 'founder_profile', None)

                    if not any([expert, visionary, founder]):
                        continue  # User has no legacy profiles

                    # 3. Create the Unified Profile Lobby
                    # We prioritize Expert data, then Founder, then Visionary to resolve conflicts
                    primary = expert or founder or visionary

                    user_profile = UserProfile.objects.create(
                        user=user,
                        slug=primary.slug if primary.slug else None,
                        location=getattr(primary, 'location', '') or '',
                        institution=getattr(visionary, 'institution', '') or '',
                        field_of_interest=getattr(visionary, 'field_of_interest', '') or '',
                        years_experience=getattr(expert, 'years_experience', 0) or 0,
                        bio_narrative=getattr(primary, 'bio_narrative', '') or '',
                        current_mission=getattr(primary, 'right_now', '') or '',
                        current_search=getattr(primary, 'current_search', None) or 'LEARNING',
                        collaboration_status=getattr(primary, 'collaboration_status', None) or 'OPEN',
                        admin_rating=getattr(primary, 'admin_rating', 0) or 0,
                        is_rating_locked=getattr(primary, 'is_rating_locked', False),
                        last_signal_update=getattr(primary, 'last_signal_update', None) or timezone.now()
                    )

                    # Fix 1: Preserve historical creation timestamp of the profile itself
                    self.preserve_timestamps(UserProfile, user_profile.pk, primary.created_at, primary.updated_at)

                    # Safely map CV file without duplicating the physical file
                    if expert and expert.cv_file:
                        user_profile.cv_file.name = expert.cv_file.name
                        user_profile.save(update_fields=['cv_file'])

                    # 4. Migrate Headlines
                    if expert:
                        for hl in expert.headlines.all():
                            ProfileHeadline.objects.create(
                                profile=user_profile, title=hl.title,
                                is_primary=hl.is_primary, order=hl.order
                            )
                    elif visionary and visionary.current_title:
                        ProfileHeadline.objects.create(
                            profile=user_profile, title=visionary.current_title, is_primary=True
                        )

                    # 5. Migrate Skills & Learning Targets
                    if expert:
                        for skill in expert.skills.all():
                            Skill.objects.create(
                                profile=user_profile, name=skill.name, context=skill.description,
                                status=Skill.SkillStatus.MASTERED, proficiency_level=skill.level,
                                admin_status=skill.admin_status
                            )
                    if visionary:
                        for target in visionary.learning_targets.all():
                            status_map = {
                                'INTERESTED': Skill.SkillStatus.INTERESTED,
                                'LEARNING': Skill.SkillStatus.LEARNING,
                                'MASTERED': Skill.SkillStatus.MASTERED,
                            }
                            Skill.objects.create(
                                profile=user_profile, name=target.skill_name, context=target.learning_motivation,
                                status=status_map.get(target.status, Skill.SkillStatus.LEARNING),
                                progress_bar=target.progress_bar
                            )

                    # 6. Migrate Credentials
                    if expert:
                        for cred in expert.credentials.all():
                            new_cred = Credential.objects.create(
                                profile=user_profile, credential_type=Credential.CredentialType.DEGREE,
                                title=cred.degree_title, issuer=cred.institution,
                                reflection=cred.personal_reflection,
                                is_admin_verified=(cred.admin_status == 'VERIFIED')
                            )
                            # Fix 2: Preserve the Credential Date
                            self.preserve_timestamps(Credential, new_cred.pk,
                                                     getattr(cred, 'created_at', primary.created_at))

                            if cred.verification_file:
                                new_cred.file_upload.name = cred.verification_file.name
                                new_cred.save(update_fields=['file_upload'])

                    if visionary:
                        for cert in visionary.certifications.all():
                            new_cert = Credential.objects.create(
                                profile=user_profile, credential_type=Credential.CredentialType.CERTIFICATE,
                                title=cert.name or "Certificate", issuer=cert.issuing_organization or "Unknown",
                                reflection=cert.learning_reflection, key_takeaways=cert.key_takeaways,
                                issue_date=cert.issue_date, url_link=cert.certificate_link
                            )
                            if cert.certificate_file:
                                new_cert.file_upload.name = cert.certificate_file.name
                                new_cert.save(update_fields=['file_upload'])

                    # 7. Migrate Portfolio Projects
                    if expert:
                        for proj in expert.projects.all():
                            new_proj = PortfolioProject.objects.create(
                                profile=user_profile, title=proj.title,
                                context=PortfolioProject.ProjectContext.REAL_WORLD,
                                role=proj.role, client_name=proj.client_name, main_description=proj.description,
                                order=proj.order
                            )
                            self.preserve_timestamps(PortfolioProject, new_proj.pk, primary.created_at)

                            # Migrate Gallery Images
                            for img in proj.gallery.all():
                                new_img = ProjectGallery.objects.create(project=new_proj, caption=img.caption)
                                new_img.image.name = img.image.name
                                new_img.save(update_fields=['image'])

                    if visionary:
                        for proj in visionary.projects.all():
                            proj_title = getattr(proj, 'name', None) or "Project"
                            new_proj = PortfolioProject.objects.create(
                                profile=user_profile, title=proj_title,
                                context=PortfolioProject.ProjectContext.PRACTICE,
                                problem_statement=proj.problem, solution_narrative=proj.solution, link=proj.link
                            )
                            # Fix 3: Preserve Visionary Project original creation date
                            self.preserve_timestamps(PortfolioProject, new_proj.pk, proj.created_at)

                            # Migrate Gallery Images
                            for img in proj.gallery.all():
                                new_img = ProjectGallery.objects.create(project=new_proj, caption=img.caption)
                                new_img.image.name = img.file.name
                                new_img.save(update_fields=['image'])

                    # 8. Migrate Work Experience (Expert)
                    if expert:
                        for exp in expert.experiences.all():
                            WorkExperience.objects.create(
                                profile=user_profile, company_name=exp.company_name, role_title=exp.role_title,
                                location_type=exp.location_type, start_date=exp.start_date, end_date=exp.end_date,
                                is_current=exp.is_current, description=exp.description
                            )

                    # 9. Migrate Content (Thoughts, Logs, Vision Blocks)
                    if expert:
                        for thought in expert.thoughts.all():
                            new_thought = ContentPost.objects.create(
                                profile=user_profile, post_type=ContentPost.PostType.ESSAY,
                                title=thought.title, content=thought.content, visibility=thought.visibility
                            )
                            # Fix 4: Preserve Expert Thought historical date
                            self.preserve_timestamps(ContentPost, new_thought.pk, thought.created_at,
                                                     thought.updated_at)

                    if visionary:
                        for log in visionary.growth_logs.all():
                            new_log = ContentPost.objects.create(
                                profile=user_profile, post_type=ContentPost.PostType.GROWTH_LOG,
                                category=log.category, title=log.title, content=log.narrative,
                                is_verified=log.is_verified
                            )

                            # Fix 5: Convert GrowthLog `date` field to aware `datetime` to preserve history!
                            if log.date:
                                historical_dt = timezone.make_aware(
                                    datetime.datetime.combine(log.date, datetime.time.min))
                            else:
                                historical_dt = primary.created_at

                            self.preserve_timestamps(ContentPost, new_log.pk, historical_dt)

                            if log.daily_photo:
                                new_log.media_proof.name = log.daily_photo.name
                                new_log.save(update_fields=['media_proof'])

                        for block in visionary.vision_blocks.all():
                            new_block = ContentPost.objects.create(
                                profile=user_profile, post_type=ContentPost.PostType.VISION_BLOCK,
                                title=block.title, content=block.content, order=block.order
                            )
                            self.preserve_timestamps(ContentPost, new_block.pk, primary.created_at)

                    # 10. Migrate Job Preferences
                    if expert:
                        for pref in expert.job_preferences.all():
                            NewJobPreference.objects.create(
                                profile=user_profile, role_title=pref.role_title,
                                work_arrangement=pref.work_arrangement, commitment_type=pref.commitment_type,
                                description=pref.description, is_active=pref.is_active
                            )

                    success_count += 1

                    # Print progress
                    if index % 50 == 0:
                        self.stdout.write(f"Processed {index}/{total_users} users...")

            except Exception as e:
                error_count += 1
                logger.error(f"Migration failed for User ID {user.id}: {str(e)}")
                identifier = getattr(user, 'phone_number', user.id)
                self.stdout.write(self.style.ERROR(f"Failed user {identifier}: {str(e)}"))

        # Final Summary
        self.stdout.write(self.style.SUCCESS(f"Migration Complete!"))
        self.stdout.write(self.style.SUCCESS(f"Successfully migrated this run: {success_count} users."))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"Failed migrations this run: {error_count} users. Check logs."))