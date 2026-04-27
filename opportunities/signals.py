# opportunities/signals.py

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import JobPost, JobApplication

# Setup a logger (This writes to your server logs instead of just the terminal)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------
# HOOK 1: THE GRAVITY PULL (JOB ALERTS)
# Triggered when a Job is created or updated.
# ------------------------------------------------------------------------
@receiver(post_save, sender=JobPost)
def trigger_gravity_pull(sender, instance, created, **kwargs):
    """
    Listens for when an Admin approves a job (Status -> ACTIVE).
    """
    # We only care if the job is ACTIVE.
    if instance.status == JobPost.Status.ACTIVE:
        # Check if this is a brand new activation (Logic for V2)
        # For now, we log that the Gravity Engine is ready to headhunt.
        logger.info(f"🚀 GRAVITY HOOK: Job '{instance.title}' is LIVE. Ready to scan for matching Visionaries.")

        # [FUTURE V2 CODE GOES HERE]:
        # users_to_alert = User.objects.filter(skills__in=instance.required_skills.all())
        # send_telegram_blast(users_to_alert)


# ------------------------------------------------------------------------
# HOOK 2: THE APPLICATION LIFECYCLE (MATCHING & NOTIFICATIONS)
# Triggered when a User applies OR when a Creator updates status.
# ------------------------------------------------------------------------
@receiver(post_save, sender=JobApplication)
def process_application_lifecycle(sender, instance, created, **kwargs):
    """
    Listens to the Application Pipeline.
    1. New Application -> Calculate Match Score.
    2. Status Change -> Notify the Applicant.
    """
    if created:
        # EVENT A: User just clicked "⚡ Link Profile"
        logger.info(
            f"⚡ MATCH HOOK: {instance.applicant.full_name} applied to '{instance.job.title}'. Calculating Score...")

        # [FUTURE V2 CODE GOES HERE]:
        # score = AI_Engine.calculate_vector_match(instance.job, instance.applicant)
        # instance.match_score = score
        # instance.save()

    else:
        # EVENT B: The Creator changed the status (Shortlisted/Rejected)

        if instance.status == JobApplication.Status.SHORTLISTED:
            logger.info(f"⭐ NOTIFY HOOK: Alert {instance.applicant.full_name} - They are SHORTLISTED!")
            # [FUTURE V2 CODE]: send_email(instance.applicant.email, "You made the shortlist!")

        elif instance.status == JobApplication.Status.REJECTED:
            logger.info(f"❌ NOTIFY HOOK: Log rejection for {instance.applicant.full_name}. No notification sent yet.")

        elif instance.status == JobApplication.Status.HIRED:
            logger.info(f"🎉 SUCCESS HOOK: {instance.applicant.full_name} was HIRED! Close the loop.")