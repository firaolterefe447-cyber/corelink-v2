"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CORELINK CATEGORY DETECTION SERVICE                        ║
║                    AI-Auto-Detect for Project Categories                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

This service provides intelligent category detection for projects based on:
1. Keyword analysis (current implementation - fast, no external dependencies)
2. Can be upgraded to use AI/ML models (OpenAI, local ML, etc.)

Architecture:
- Keyword-based scoring system with weighted terms
- Confidence threshold for auto-detection
- Fallback to manual selection if confidence is low
- Extensible for future AI integration
"""

import re
from typing import Dict, Tuple, Optional
from collections import Counter


class CategoryDetector:
    """
    Intelligent category detection using keyword analysis.
    Can be extended with AI/ML models in the future.
    """

    # Keyword mappings for each category with weights
    CATEGORY_KEYWORDS = {
        'SOFTWARE_DATA': {
            # High weight terms (3.0)
            'python': 3.0, 'javascript': 3.0, 'react': 3.0, 'angular': 3.0,
            'django': 3.0, 'flask': 3.0, 'node': 3.0, 'api': 3.0,
            'machine learning': 3.0, 'deep learning': 3.0, 'ai': 3.0,
            'tensorflow': 3.0, 'pytorch': 3.0, 'data science': 3.0,
            'database': 3.0, 'sql': 3.0, 'mongodb': 3.0, 'postgresql': 3.0,
            'aws': 3.0, 'azure': 3.0, 'gcp': 3.0, 'cloud': 3.0,
            'docker': 3.0, 'kubernetes': 3.0, 'devops': 3.0,
            'github': 3.0, 'gitlab': 3.0, 'repository': 3.0,
            # Medium weight terms (2.0)
            'app': 2.0, 'application': 2.0, 'software': 2.0, 'web': 2.0,
            'frontend': 2.0, 'backend': 2.0, 'full stack': 2.0,
            'algorithm': 2.0, 'model': 2.0, 'neural': 2.0,
            'analytics': 2.0, 'dashboard': 2.0, 'visualization': 2.0,
            'code': 2.0, 'programming': 2.0, 'development': 2.0,
            # Low weight terms (1.0)
            'tech': 1.0, 'digital': 1.0, 'platform': 1.0, 'system': 1.0,
        },
        'HARDWARE_ROBOTICS': {
            # High weight terms
            'robot': 3.0, 'robotics': 3.0, 'arduino': 3.0, 'raspberry': 3.0,
            'microcontroller': 3.0, 'embedded': 3.0, 'pcb': 3.0, 'circuit': 3.0,
            'sensor': 3.0, 'actuator': 3.0, 'motor': 3.0, 'drone': 3.0,
            '3d print': 3.0, 'additive manufacturing': 3.0, 'cad': 3.0,
            'firmware': 3.0, 'hardware': 3.0, 'electronic': 3.0,
            # Medium weight terms
            'iot': 2.0, 'automation': 2.0, 'mechatronics': 2.0,
            'prototype': 2.0, 'manufacturing': 2.0, 'assembly': 2.0,
            'engineering': 2.0, 'mechanical': 2.0, 'electrical': 2.0,
            # Low weight terms
            'device': 1.0, 'gadget': 1.0, 'tool': 1.0, 'machine': 1.0,
        },
        'MEDICAL_CLINICAL': {
            # High weight terms
            'clinical': 3.0, 'medical': 3.0, 'patient': 3.0, 'hospital': 3.0,
            'trial': 3.0, 'research': 3.0, 'study': 3.0, 'treatment': 3.0,
            'therapy': 3.0, 'diagnosis': 3.0, 'pharmaceutical': 3.0,
            'biotech': 3.0, 'biotechnology': 3.0, 'drug': 3.0, 'medicine': 3.0,
            'healthcare': 3.0, 'health care': 3.0, 'physician': 3.0,
            'nurse': 3.0, 'doctor': 3.0, 'surgeon': 3.0, 'surgery': 3.0,
            'epidemiology': 3.0, 'public health': 3.0,
            # Medium weight terms
            'cardiology': 2.0, 'neurology': 2.0, 'oncology': 2.0,
            'pediatrics': 2.0, 'radiology': 2.0, 'pathology': 2.0,
            'laboratory': 2.0, 'lab': 2.0, 'cohort': 2.0, 'placebo': 2.0,
            'intervention': 2.0, 'outcome': 2.0, 'protocol': 2.0,
            # Low weight terms
            'clinic': 1.0, 'health': 1.0, 'wellness': 1.0, 'care': 1.0,
        },
        'LEGAL_POLICY': {
            # High weight terms
            'law': 3.0, 'legal': 3.0, 'lawyer': 3.0, 'attorney': 3.0,
            'court': 3.0, 'litigation': 3.0, 'contract': 3.0, 'regulation': 3.0,
            'policy': 3.0, 'government': 3.0, 'legislation': 3.0,
            'compliance': 3.0, 'regulatory': 3.0, 'jurisdiction': 3.0,
            'constitutional': 3.0, 'criminal': 3.0, 'civil': 3.0,
            'advocacy': 3.0, 'rights': 3.0, 'justice': 3.0,
            # Medium weight terms
            'bill': 2.0, 'statute': 2.0, 'ordinance': 2.0, 'code': 2.0,
            'administrative': 2.0, 'legislative': 2.0, 'judicial': 2.0,
            'pro bono': 2.0, 'public interest': 2.0, 'nonprofit': 2.0,
            # Low weight terms
            'rule': 1.0, 'governmental': 1.0, 'official': 1.0, 'civic': 1.0,
        },
        'SCIENCE_RESEARCH': {
            # High weight terms
            'laboratory': 3.0, 'experiment': 3.0, 'hypothesis': 3.0,
            'scientific': 3.0, 'research': 3.0, 'academia': 3.0, 'academic': 3.0,
            'university': 3.0, 'phd': 3.0, 'doctoral': 3.0, 'thesis': 3.0,
            'publication': 3.0, 'journal': 3.0, 'peer review': 3.0,
            'chemistry': 3.0, 'physics': 3.0, 'biology': 3.0, 'geology': 3.0,
            'astronomy': 3.0, 'ecology': 3.0, 'genetics': 3.0,
            'microscope': 3.0, 'spectrometer': 3.0, 'analysis': 3.0,
            # Medium weight terms
            'data': 2.0, 'methodology': 2.0, 'results': 2.0, 'findings': 2.0,
            'conclusion': 2.0, 'abstract': 2.0, 'citation': 2.0,
            'grant': 2.0, 'funding': 2.0, 'proposal': 2.0,
            'lab': 2.0, 'field work': 2.0, 'fieldwork': 2.0,
            # Low weight terms
            'science': 1.0, 'study': 1.0, 'investigation': 1.0, 'discovery': 1.0,
        },
        'DESIGN_UX': {
            # High weight terms
            'design': 3.0, 'ux': 3.0, 'ui': 3.0, 'user experience': 3.0,
            'user interface': 3.0, 'figma': 3.0, 'sketch': 3.0, 'adobe': 3.0,
            'photoshop': 3.0, 'illustrator': 3.0, 'in design': 3.0,
            'wireframe': 3.0, 'prototype': 3.0, 'mockup': 3.0,
            'graphic': 3.0, 'branding': 3.0, 'logo': 3.0, 'identity': 3.0,
            'typography': 3.0, 'layout': 3.0, 'color': 3.0,
            # Medium weight terms
            'user research': 2.0, 'usability': 2.0, 'accessibility': 2.0,
            'interaction': 2.0, 'visual': 2.0, 'creative': 2.0,
            'product design': 2.0, 'service design': 2.0,
            'design system': 2.0, 'component': 2.0,
            # Low weight terms
            'art': 1.0, 'creative': 1.0, 'aesthetic': 1.0, 'style': 1.0,
        },
        'ARCHITECTURE_CIVIL': {
            # High weight terms
            'architecture': 3.0, 'architect': 3.0, 'building': 3.0,
            'structural': 3.0, 'civil': 3.0, 'engineering': 3.0,
            'construction': 3.0, 'blueprint': 3.0, 'floor plan': 3.0,
            'revit': 3.0, 'autocad': 3.0, 'bim': 3.0,
            'sustainable': 3.0, 'leed': 3.0, 'green building': 3.0,
            'urban': 3.0, 'planning': 3.0, 'landscape': 3.0,
            'infrastructure': 3.0, 'bridge': 3.0, 'road': 3.0,
            # Medium weight terms
            'design': 2.0, 'renovation': 2.0, 'restoration': 2.0,
            'interior': 2.0, 'exterior': 2.0, 'facade': 2.0,
            'site': 2.0, 'development': 2.0, 'real estate': 2.0,
            'material': 2.0, 'concrete': 2.0, 'steel': 2.0,
            # Low weight terms
            'house': 1.0, 'home': 1.0, 'office': 1.0, 'space': 1.0,
        },
        'BUSINESS_FINANCE': {
            # High weight terms
            'business': 3.0, 'startup': 3.0, 'entrepreneur': 3.0,
            'finance': 3.0, 'financial': 3.0, 'investment': 3.0,
            'venture capital': 3.0, 'funding': 3.0, 'pitch': 3.0,
            'revenue': 3.0, 'profit': 3.0, 'growth': 3.0, 'scale': 3.0,
            'marketing': 3.0, 'sales': 3.0, 'strategy': 3.0,
            'ceo': 3.0, 'founder': 3.0, 'co-founder': 3.0,
            'accounting': 3.0, 'audit': 3.0, 'tax': 3.0,
            # Medium weight terms
            'business model': 2.0, 'market': 2.0, 'customer': 2.0,
            'product': 2.0, 'service': 2.0, 'operations': 2.0,
            'management': 2.0, 'leadership': 2.0, 'team': 2.0,
            'valuation': 2.0, 'equity': 2.0, 'shares': 2.0,
            # Low weight terms
            'company': 1.0, 'corporate': 1.0, 'enterprise': 1.0, 'commercial': 1.0,
        },
        'MARKETING_MEDIA': {
            # High weight terms
            'marketing': 3.0, 'advertising': 3.0, 'brand': 3.0,
            'social media': 3.0, 'content': 3.0, 'campaign': 3.0,
            'seo': 3.0, 'sem': 3.0, 'ppc': 3.0, 'analytics': 3.0,
            'journalism': 3.0, 'news': 3.0, 'media': 3.0, 'press': 3.0,
            'public relations': 3.0, 'pr': 3.0, 'communications': 3.0,
            'influencer': 3.0, 'viral': 3.0, 'engagement': 3.0,
            # Medium weight terms
            'copywriting': 2.0, 'storytelling': 2.0, 'narrative': 2.0,
            'audience': 2.0, 'target market': 2.0, 'demographics': 2.0,
            'conversion': 2.0, 'funnel': 2.0, 'lead': 2.0,
            'video': 2.0, 'audio': 2.0, 'podcast': 2.0,
            # Low weight terms
            'promotion': 1.0, 'outreach': 1.0, 'publicity': 1.0, 'message': 1.0,
        },
        'ARTS_CREATIVE': {
            # High weight terms
            'film': 3.0, 'movie': 3.0, 'cinema': 3.0, 'video': 3.0,
            'photography': 3.0, 'photo': 3.0, 'camera': 3.0,
            'music': 3.0, 'song': 3.0, 'album': 3.0, 'audio': 3.0,
            'art': 3.0, 'artist': 3.0, 'painting': 3.0, 'sculpture': 3.0,
            'theater': 3.0, 'theatre': 3.0, 'performance': 3.0,
            'creative': 3.0, 'director': 3.0, 'producer': 3.0,
            'exhibition': 3.0, 'gallery': 3.0, 'museum': 3.0,
            # Medium weight terms
            'documentary': 2.0, 'short film': 2.0, 'animation': 2.0,
            'portrait': 2.0, 'landscape': 2.0, 'composition': 2.0,
            'composition': 2.0, 'choreography': 2.0, 'dance': 2.0,
            'studio': 2.0, 'portfolio': 2.0, 'showcase': 2.0,
            # Low weight terms
            'visual': 1.0, 'creative work': 1.0, 'artistic': 1.0, 'cultural': 1.0,
        },
        'EDUCATION_TRAINING': {
            # High weight terms
            'education': 3.0, 'teaching': 3.0, 'teacher': 3.0,
            'training': 3.0, 'curriculum': 3.0, 'course': 3.0,
            'lesson': 3.0, 'workshop': 3.0, 'seminar': 3.0,
            'learning': 3.0, 'e-learning': 3.0, 'online course': 3.0,
            'student': 3.0, 'classroom': 3.0, 'school': 3.0,
            'instructional design': 3.0, 'pedagogy': 3.0,
            'certification': 3.0, 'certificate': 3.0, 'bootcamp': 3.0,
            # Medium weight terms
            'instructor': 2.0, 'educator': 2.0, 'professor': 2.0,
            'assessment': 2.0, 'evaluation': 2.0, 'grading': 2.0,
            'mooc': 2.0, 'tutorial': 2.0, 'guide': 2.0,
            'skill development': 2.0, 'professional development': 2.0,
            # Low weight terms
            'study': 1.0, 'class': 1.0, 'lecture': 1.0, 'academic': 1.0,
        },
        'OPERATIONS_TRADES': {
            # High weight terms
            'operations': 3.0, 'logistics': 3.0, 'supply chain': 3.0,
            'inventory': 3.0, 'warehouse': 3.0, 'distribution': 3.0,
            'culinary': 3.0, 'chef': 3.0, 'cooking': 3.0, 'kitchen': 3.0,
            'restaurant': 3.0, 'food service': 3.0, 'hospitality': 3.0,
            'plumbing': 3.0, 'electrical': 3.0, 'carpentry': 3.0,
            'hvac': 3.0, 'welding': 3.0, 'trade': 3.0,
            'maintenance': 3.0, 'repair': 3.0, 'service': 3.0,
            # Medium weight terms
            'procurement': 2.0, 'sourcing': 2.0, 'vendor': 2.0,
            'quality control': 2.0, 'inspection': 2.0, 'safety': 2.0,
            'recipe': 2.0, 'menu': 2.0, 'catering': 2.0,
            'skilled trade': 2.0, 'craftsmanship': 2.0, 'technician': 2.0,
            # Low weight terms
            'operations management': 1.0, 'service industry': 1.0, 'trade work': 1.0,
        },
        'OTHER': {
            # Low weight generic terms (fallback)
            'project': 1.0, 'work': 1.0, 'initiative': 1.0, 'program': 1.0,
        }
    }

    # Confidence threshold for auto-detection
    CONFIDENCE_THRESHOLD = 2.0

    @classmethod
    def detect_category(cls, title: str = '', description: str = '', role: str = '') -> Tuple[Optional[str], float]:
        """
        Detect the most likely category based on project text.

        Args:
            title: Project title
            description: Project description
            role: User's role in the project

        Returns:
            Tuple of (category_code, confidence_score)
            Returns (None, 0.0) if no category meets threshold
        """
        # Combine all text for analysis
        combined_text = f"{title} {description} {role}".lower()

        # Score each category
        category_scores = {}

        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            score = 0.0
            for keyword, weight in keywords.items():
                # Count occurrences (case-insensitive)
                occurrences = len(re.findall(rf'\b{re.escape(keyword)}\b', combined_text))
                score += occurrences * weight

            if score > 0:
                category_scores[category] = score

        # Find the highest scoring category
        if not category_scores:
            return None, 0.0

        best_category = max(category_scores.items(), key=lambda x: x[1])
        category_code, confidence = best_category

        # Only return if confidence meets threshold
        if confidence >= cls.CONFIDENCE_THRESHOLD:
            return category_code, confidence

        return None, 0.0

    @classmethod
    def get_category_suggestions(cls, title: str = '', description: str = '', role: str = '', top_n: int = 3) -> list:
        """
        Get top N category suggestions with confidence scores.

        Args:
            title: Project title
            description: Project description
            role: User's role in the project
            top_n: Number of suggestions to return

        Returns:
            List of tuples: [(category_code, confidence_score), ...]
        """
        combined_text = f"{title} {description} {role}".lower()
        category_scores = {}

        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            score = 0.0
            for keyword, weight in keywords.items():
                occurrences = len(re.findall(rf'\b{re.escape(keyword)}\b', combined_text))
                score += occurrences * weight

            if score > 0:
                category_scores[category] = score

        # Sort by score (descending) and return top N
        sorted_scores = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:top_n]


def detect_project_category(title: str = '', description: str = '', role: str = '') -> Dict:
    """
    Convenience function for category detection.

    Returns:
        Dict with keys:
        - category: detected category code (or None)
        - confidence: confidence score (0.0 if no detection)
        - suggestions: list of top 3 suggestions
    """
    category, confidence = CategoryDetector.detect_category(title, description, role)
    suggestions = CategoryDetector.get_category_suggestions(title, description, role)

    return {
        'category': category,
        'confidence': round(confidence, 2),
        'suggestions': [(code, round(score)) for code, score in suggestions]
    }
