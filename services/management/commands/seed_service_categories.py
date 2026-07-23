"""
Management command to seed initial service categories, subcategories, types, and tags.
Run: python manage.py seed_service_categories
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from services.models import ServiceCategory, ServiceSubcategory, ServiceTag, ServiceType


class Command(BaseCommand):
    help = 'Seeds the database with common service categories, subcategories, types, and tags'

    def handle(self, *args, **options):
        self.stdout.write('Starting to seed service categories...')

        # Seed Service Types
        self.stdout.write('Seeding service types...')
        service_types_data = [
            {'name': 'One-time Project', 'slug': 'one-time', 'description': 'Complete project delivered once', 'icon': '📦', 'order': 1},
            {'name': 'Recurring Service', 'slug': 'recurring', 'description': 'Ongoing subscription or retainer', 'icon': '🔄', 'order': 2},
            {'name': 'Consultation', 'slug': 'consultation', 'description': 'Expert advice and strategy sessions', 'icon': '💡', 'order': 3},
            {'name': 'Maintenance', 'slug': 'maintenance', 'description': 'Support and upkeep services', 'icon': '🔧', 'order': 4},
            {'name': 'Hourly Rate', 'slug': 'hourly', 'description': 'Charged by the hour', 'icon': '⏱️', 'order': 5},
        ]

        for st_data in service_types_data:
            ServiceType.objects.get_or_create(
                slug=st_data['slug'],
                defaults={
                    'name': st_data['name'],
                    'description': st_data['description'],
                    'icon': st_data['icon'],
                    'order': st_data['order'],
                    'is_active': True
                }
            )
        self.stdout.write(self.style.SUCCESS(f'Created {len(service_types_data)} service types'))

        # Seed Categories and Subcategories
        self.stdout.write('Seeding categories and subcategories...')
        categories_data = {
            'Design & Creative': {
                'slug': 'design-creative',
                'color': '#EC4899',
                'description': 'Visual design, branding, and creative services',
                'order': 1,
                'subcategories': [
                    {'name': 'Graphic Design', 'slug': 'graphic-design', 'order': 1},
                    {'name': 'UI/UX Design', 'slug': 'ui-ux-design', 'order': 2},
                    {'name': 'Logo & Branding', 'slug': 'logo-branding', 'order': 3},
                    {'name': 'Illustration', 'slug': 'illustration', 'order': 4},
                    {'name': 'Video Editing', 'slug': 'video-editing', 'order': 5},
                    {'name': 'Animation', 'slug': 'animation', 'order': 6},
                    {'name': 'Photography', 'slug': 'photography', 'order': 7},
                    {'name': '3D Modeling', 'slug': '3d-modeling', 'order': 8},
                ]
            },
            'Development & IT': {
                'slug': 'development-it',
                'color': '#3B82F6',
                'description': 'Software development, web, and technical services',
                'order': 2,
                'subcategories': [
                    {'name': 'Web Development', 'slug': 'web-development', 'order': 1},
                    {'name': 'Mobile App Development', 'slug': 'mobile-app-development', 'order': 2},
                    {'name': 'Backend Development', 'slug': 'backend-development', 'order': 3},
                    {'name': 'Frontend Development', 'slug': 'frontend-development', 'order': 4},
                    {'name': 'Database Management', 'slug': 'database-management', 'order': 5},
                    {'name': 'DevOps & Cloud', 'slug': 'devops-cloud', 'order': 6},
                    {'name': 'API Development', 'slug': 'api-development', 'order': 7},
                    {'name': 'Quality Assurance', 'slug': 'quality-assurance', 'order': 8},
                ]
            },
            'Marketing & Sales': {
                'slug': 'marketing-sales',
                'color': '#10B981',
                'description': 'Digital marketing, SEO, and sales services',
                'order': 3,
                'subcategories': [
                    {'name': 'Digital Marketing', 'slug': 'digital-marketing', 'order': 1},
                    {'name': 'SEO', 'slug': 'seo', 'order': 2},
                    {'name': 'Social Media Marketing', 'slug': 'social-media-marketing', 'order': 3},
                    {'name': 'Content Marketing', 'slug': 'content-marketing', 'order': 4},
                    {'name': 'Email Marketing', 'slug': 'email-marketing', 'order': 5},
                    {'name': 'PPC Advertising', 'slug': 'ppc-advertising', 'order': 6},
                    {'name': 'Copywriting', 'slug': 'copywriting', 'order': 7},
                    {'name': 'Public Relations', 'slug': 'public-relations', 'order': 8},
                ]
            },
            'Business & Consulting': {
                'slug': 'business-consulting',
                'color': '#F59E0B',
                'description': 'Business strategy, consulting, and professional services',
                'order': 4,
                'subcategories': [
                    {'name': 'Business Strategy', 'slug': 'business-strategy', 'order': 1},
                    {'name': 'Financial Consulting', 'slug': 'financial-consulting', 'order': 2},
                    {'name': 'Legal Consulting', 'slug': 'legal-consulting', 'order': 3},
                    {'name': 'HR Consulting', 'slug': 'hr-consulting', 'order': 4},
                    {'name': 'Project Management', 'slug': 'project-management', 'order': 5},
                    {'name': 'Market Research', 'slug': 'market-research', 'order': 6},
                    {'name': 'Business Planning', 'slug': 'business-planning', 'order': 7},
                    {'name': 'Startup Consulting', 'slug': 'startup-consulting', 'order': 8},
                ]
            },
            'Writing & Translation': {
                'slug': 'writing-translation',
                'color': '#8B5CF6',
                'description': 'Content writing, translation, and language services',
                'order': 5,
                'subcategories': [
                    {'name': 'Content Writing', 'slug': 'content-writing', 'order': 1},
                    {'name': 'Technical Writing', 'slug': 'technical-writing', 'order': 2},
                    {'name': 'Creative Writing', 'slug': 'creative-writing', 'order': 3},
                    {'name': 'Translation', 'slug': 'translation', 'order': 4},
                    {'name': 'Proofreading & Editing', 'slug': 'proofreading-editing', 'order': 5},
                    {'name': 'Ghostwriting', 'slug': 'ghostwriting', 'order': 6},
                    {'name': 'Transcription', 'slug': 'transcription', 'order': 7},
                ]
            },
            'Data & Analytics': {
                'slug': 'data-analytics',
                'color': '#06B6D4',
                'description': 'Data science, analytics, and research services',
                'order': 6,
                'subcategories': [
                    {'name': 'Data Analysis', 'slug': 'data-analysis', 'order': 1},
                    {'name': 'Data Science', 'slug': 'data-science', 'order': 2},
                    {'name': 'Machine Learning', 'slug': 'machine-learning', 'order': 3},
                    {'name': 'Data Visualization', 'slug': 'data-visualization', 'order': 4},
                    {'name': 'Business Intelligence', 'slug': 'business-intelligence', 'order': 5},
                    {'name': 'Statistical Analysis', 'slug': 'statistical-analysis', 'order': 6},
                ]
            },
            'Education & Training': {
                'slug': 'education-training',
                'color': '#EF4444',
                'description': 'Teaching, tutoring, and educational services',
                'order': 7,
                'subcategories': [
                    {'name': 'Online Tutoring', 'slug': 'online-tutoring', 'order': 1},
                    {'name': 'Course Creation', 'slug': 'course-creation', 'order': 2},
                    {'name': 'Corporate Training', 'slug': 'corporate-training', 'order': 3},
                    {'name': 'Language Teaching', 'slug': 'language-teaching', 'order': 4},
                    {'name': 'Curriculum Development', 'slug': 'curriculum-development', 'order': 5},
                ]
            },
            'Admin & Support': {
                'slug': 'admin-support',
                'color': '#6B7280',
                'description': 'Virtual assistance and administrative support',
                'order': 8,
                'subcategories': [
                    {'name': 'Virtual Assistant', 'slug': 'virtual-assistant', 'order': 1},
                    {'name': 'Customer Support', 'slug': 'customer-support', 'order': 2},
                    {'name': 'Data Entry', 'slug': 'data-entry', 'order': 3},
                    {'name': 'Web Research', 'slug': 'web-research', 'order': 4},
                    {'name': 'Transcription', 'slug': 'transcription', 'order': 5},
                    {'name': 'Account Management', 'slug': 'account-management', 'order': 6},
                ]
            },
        }

        total_subcategories = 0
        for cat_name, cat_data in categories_data.items():
            category, created = ServiceCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_name,
                    'description': cat_data['description'],
                    'color': cat_data['color'],
                    'order': cat_data['order'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'  Created category: {cat_name}')
            else:
                self.stdout.write(f'  Category already exists: {cat_name}')

            for sub_data in cat_data['subcategories']:
                ServiceSubcategory.objects.get_or_create(
                    slug=sub_data['slug'],
                    category=category,
                    defaults={
                        'name': sub_data['name'],
                        'order': sub_data['order'],
                        'is_active': True
                    }
                )
                total_subcategories += 1

        self.stdout.write(self.style.SUCCESS(f'Created {len(categories_data)} categories with {total_subcategories} subcategories'))

        # Seed Tags
        self.stdout.write('Seeding tags...')
        tags_data = [
            # Design tags
            {'name': 'Adobe Creative Suite', 'slug': 'adobe-creative-suite', 'is_featured': True},
            {'name': 'Figma', 'slug': 'figma', 'is_featured': True},
            {'name': 'Sketch', 'slug': 'sketch', 'is_featured': False},
            {'name': 'Canva', 'slug': 'canva', 'is_featured': False},
            {'name': 'Photoshop', 'slug': 'photoshop', 'is_featured': True},
            {'name': 'Illustrator', 'slug': 'illustrator', 'is_featured': True},
            {'name': 'After Effects', 'slug': 'after-effects', 'is_featured': False},
            {'name': 'Premiere Pro', 'slug': 'premiere-pro', 'is_featured': False},
            
            # Development tags
            {'name': 'Python', 'slug': 'python', 'is_featured': True},
            {'name': 'JavaScript', 'slug': 'javascript', 'is_featured': True},
            {'name': 'React', 'slug': 'react', 'is_featured': True},
            {'name': 'Vue.js', 'slug': 'vuejs', 'is_featured': False},
            {'name': 'Node.js', 'slug': 'nodejs', 'is_featured': True},
            {'name': 'Django', 'slug': 'django', 'is_featured': False},
            {'name': 'WordPress', 'slug': 'wordpress', 'is_featured': True},
            {'name': 'Shopify', 'slug': 'shopify', 'is_featured': True},
            {'name': 'AWS', 'slug': 'aws', 'is_featured': True},
            {'name': 'Docker', 'slug': 'docker', 'is_featured': False},
            {'name': 'Kubernetes', 'slug': 'kubernetes', 'is_featured': False},
            {'name': 'Git', 'slug': 'git', 'is_featured': False},
            
            # Marketing tags
            {'name': 'Google Analytics', 'slug': 'google-analytics', 'is_featured': True},
            {'name': 'Google Ads', 'slug': 'google-ads', 'is_featured': True},
            {'name': 'Facebook Ads', 'slug': 'facebook-ads', 'is_featured': True},
            {'name': 'Instagram Marketing', 'slug': 'instagram-marketing', 'is_featured': True},
            {'name': 'LinkedIn Marketing', 'slug': 'linkedin-marketing', 'is_featured': False},
            {'name': 'Email Marketing', 'slug': 'email-marketing', 'is_featured': True},
            {'name': 'SEO', 'slug': 'seo', 'is_featured': True},
            {'name': 'Content Strategy', 'slug': 'content-strategy', 'is_featured': False},
            
            # Business tags
            {'name': 'Business Plan', 'slug': 'business-plan', 'is_featured': True},
            {'name': 'Financial Modeling', 'slug': 'financial-modeling', 'is_featured': False},
            {'name': 'Market Analysis', 'slug': 'market-analysis', 'is_featured': False},
            {'name': 'Agile', 'slug': 'agile', 'is_featured': True},
            {'name': 'Scrum', 'slug': 'scrum', 'is_featured': False},
            {'name': 'Lean Startup', 'slug': 'lean-startup', 'is_featured': False},
            
            # Writing tags
            {'name': 'Blog Writing', 'slug': 'blog-writing', 'is_featured': True},
            {'name': 'Technical Writing', 'slug': 'technical-writing', 'is_featured': False},
            {'name': 'Creative Writing', 'slug': 'creative-writing', 'is_featured': False},
            {'name': 'English', 'slug': 'english', 'is_featured': True},
            {'name': 'Spanish', 'slug': 'spanish', 'is_featured': False},
            {'name': 'French', 'slug': 'french', 'is_featured': False},
            {'name': 'German', 'slug': 'german', 'is_featured': False},
            {'name': 'Arabic', 'slug': 'arabic', 'is_featured': False},
            {'name': 'Amharic', 'slug': 'amharic', 'is_featured': False},
            
            # Data tags
            {'name': 'Excel', 'slug': 'excel', 'is_featured': True},
            {'name': 'Tableau', 'slug': 'tableau', 'is_featured': True},
            {'name': 'Power BI', 'slug': 'power-bi', 'is_featured': True},
            {'name': 'SQL', 'slug': 'sql', 'is_featured': True},
            {'name': 'Pandas', 'slug': 'pandas', 'is_featured': False},
            {'name': 'NumPy', 'slug': 'numpy', 'is_featured': False},
            {'name': 'TensorFlow', 'slug': 'tensorflow', 'is_featured': False},
            {'name': 'PyTorch', 'slug': 'pytorch', 'is_featured': False},
            
            # General tags
            {'name': 'Fast Delivery', 'slug': 'fast-delivery', 'is_featured': True},
            {'name': 'Professional', 'slug': 'professional', 'is_featured': True},
            {'name': 'Experienced', 'slug': 'experienced', 'is_featured': False},
            {'name': 'Remote Work', 'slug': 'remote-work', 'is_featured': True},
            {'name': 'Flexible', 'slug': 'flexible', 'is_featured': False},
        ]

        for tag_data in tags_data:
            ServiceTag.objects.get_or_create(
                slug=tag_data['slug'],
                defaults={
                    'name': tag_data['name'],
                    'is_featured': tag_data['is_featured'],
                    'usage_count': 0
                }
            )

        self.stdout.write(self.style.SUCCESS(f'Created {len(tags_data)} tags'))

        self.stdout.write(self.style.SUCCESS('\nSuccessfully seeded all service categories, subcategories, types, and tags!'))
