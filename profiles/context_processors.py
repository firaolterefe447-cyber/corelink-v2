# profiles/context_processors.py
from profiles.models import CompanyMember


def role_and_company_context(request):
    """
    Infects every template with:
    1. 'managed_companies' if the user has Admin/Owner rights anywhere.
    2. Universal, clean, and human-centric UI text to dynamically change dashboard labels.
    """
    context = {
        'user_managed_companies': [],
        'has_company_access': False,
        'is_founder': False,
        'is_expert': False,
        'is_visionary': False,
        'role_text': {}
    }

    if request.user.is_authenticated:
        user = request.user

        # 1. Company Access Logic
        managed_memberships = CompanyMember.objects.filter(
            user=user,
            is_active=True,
            role__in=['OWNER', 'ADMIN']
        ).select_related('company')

        context['user_managed_companies'] = [m.company for m in managed_memberships]
        context['has_company_access'] = managed_memberships.exists()

        # 2. Role Extraction
        role = getattr(user, 'role', 'VISIONARY')
        context['is_founder'] = (role == 'FOUNDER')
        context['is_expert'] = (role == 'EXPERT')
        context['is_visionary'] = (role == 'VISIONARY')

        # 3. Clean, Universal UI Text
        context['role_text'] = {
            'exp_title': 'Experience & Journey',
            'exp_desc': 'Log your professional jobs, past roles, volunteer work, or community activities to showcase your path.',

            'edu_title': 'Education & Certifications',
            'edu_desc': 'Add your degrees, professional certifications, online courses, or training programs that shape your knowledge.',

            'skill_title': 'Skills & Abilities',
            'skill_desc': 'List the tools, practices, and abilities you have mastered, are actively building, or are eager to learn.',

            'proj_title': 'Projects & Portfolio',
            'proj_desc': 'Showcase your best work, professional case studies, and personal projects to build a strong portfolio.',

            'content_title': 'Updates & Insights',
            'content_desc': 'Share industry insights, daily learnings, key milestones, or your ideas for the future.'
        }

    return context