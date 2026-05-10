# CoreLink Platform - Product Requirements Document
## Current Implementation Deep Dive Documentation

**Document Version:** 1.0  
**Last Updated:** May 6, 2026  
**Status:** Production Implementation Analysis  
**Platform:** Django-based Professional Networking & Collaboration Platform

---

## Executive Summary

CoreLink is a comprehensive professional networking and collaboration platform designed to connect talent, opportunities, and teams in the Ethiopian market and beyond. The platform implements a modern "fluid portfolio" architecture where users can showcase their skills, projects, and real-time activities while discovering opportunities for collaboration, employment, and partnership.

### Core Value Proposition
- **Real-Time Professional Identity**: Dynamic "Right Now" feed that showcases what users are currently working on
- **Skill-Based Matching**: AI-powered skill taxonomy for intelligent opportunity matching
- **Team Formation**: Tools for creating and managing project teams with application workflows
- **Opportunity Marketplace**: Comprehensive job board with challenge-based hiring
- **Direct Messaging**: Built-in communication system for professional networking

### Target Users
- **Professionals**: Job seekers, freelancers, and experts looking for opportunities
- **Founders/Entrepreneurs**: Building teams and finding co-founders
- **Companies**: Posting jobs, challenges, and finding talent
- **Students/Learners**: Building portfolios and finding mentorship

---

## 1. Core Platform Architecture

### 1.1 Technology Stack
- **Backend Framework**: Django 4.x (Python)
- **Database**: SQLite (development), PostgreSQL (production)
- **Frontend**: Django Templates with TailwindCSS
- **Authentication**: Django Allauth with custom extensions
- **Internationalization**: Django i18n (English, Amharic)
- **File Storage**: Local filesystem with cloud-ready architecture
- **Real-time Features**: AJAX-based messaging and feed updates

### 1.2 Application Structure
The platform is organized into modular Django applications:

```
corelink/
├── accounts/          # Authentication, user management, onboarding
├── profiles/          # User profiles, portfolios, company profiles
├── workspace/         # Teams, messaging, collaboration hub
├── network/          # Professional networking feed (Nexus)
├── opportunities/    # Job board, applications, skill taxonomy
├── content/          # Content management system
├── core/             # Shared utilities, base models
├── operations/       # Admin operations and management
└── subscriptions/    # User subscription management
```

### 1.3 URL Routing Structure
```
/                           # Landing page
/auth/                      # Authentication flows
/workspace/                 # Main collaboration hub
/workspace/dashboard/       # User dashboard
/workspace/messages/       # Messaging system
/teams/                     # Team management
/nexus/                     # Network discovery feed
/opportunities/             # Job marketplace
/p/                         # Public profiles
/company/                   # Company profiles
/ops/                       # Admin operations
```

---

## 2. User Profile System

### 2.1 Unified Portfolio Architecture

The platform uses a "Fluid Lego Block" architecture that replaces rigid profile types with a unified, modular system.

**Core Model: UserProfile**
- Primary identity layer for all users
- One-to-one relationship with Django User model
- Auto-generated SEO-friendly slugs
- Signal-based activity tracking

**Key Fields:**
- `slug`: Unique URL identifier
- `location`: Geographic location
- `institution`: Educational or organizational affiliation
- `field_of_interest`: Primary professional domain
- `years_experience`: Experience level
- `bio_narrative`: Long-form biography
- `current_mission`: Real-time focus statement
- `current_search`: Current objective (LEARNING, COLLABORATION, EMPLOYMENT, MENTORSHIP, COFOUNDING, FREELANCE)
- `collaboration_status`: Availability (OPEN, BUSY, CLOSED)
- `admin_rating`: Platform quality score (0-5)
- `cv_file`: Resume/CV upload

### 2.2 Modular Profile Components

#### ProfileHeadline
- Multiple professional identities per user
- Primary headline selection
- Custom ordering
- Example: "Senior Developer" and "Angel Investor"

#### WorkExperience
- Company name and role title
- Location type (REMOTE, ON_SITE, HYBRID)
- Start/end dates with current position flag
- Role description

#### Credential
- Unified vault for degrees, certificates, courses
- Credential types: DEGREE, CERTIFICATE, COURSE
- Issuing organization and verification
- File upload and verification URL
- Admin verification flag
- Personal reflection and key takeaways

#### Skill
- Progressive skill tracking: INTERESTED → LEARNING → MASTERED
- Proficiency levels: JUNIOR, SENIOR, MASTER
- Progress bar (0-100%)
- Context and motivation for each skill
- Admin status tracking

#### PortfolioProject
- Proof-of-work showcase
- Project contexts: PRACTICE, REAL_WORLD, STARTUP
- Problem statement and solution narrative
- Client name and role
- Live link/GitHub integration
- Image gallery support
- Custom ordering

#### ContentPost
- Unified publishing for growth logs, essays, vision blocks
- Post types: GROWTH_LOG, ESSAY, VISION_BLOCK
- Categories: LEARNING, WORK, LIFE
- Markdown body content
- Media proof attachments
- Public/private visibility
- Verification system

### 2.3 Real-Time Networking Intent

#### RightNowPost (Core Feed Model)
- **Purpose**: Real-time status updates combined with social feed
- **Dual Function**: Acts as feed post AND current profile focus
- **Key Features**:
  - Networking intent classification
  - Rich link metadata caching (Open Graph scraping)
  - Denormalized metrics for performance
  - Active focus pinning system

**Fields:**
- `current_search`: What user is looking for
- `collaboration_status`: Current availability
- `title`: Headline/milestone
- `body_narrative`: Update content (Markdown)
- `external_link`: Shared resource URL
- `link_title/description/image_url`: Cached metadata
- `views_count/clicks_count/likes_count/comments_count`: Performance metrics
- `is_published`: Global feed visibility
- `is_active_focus`: Profile pinning status

#### RightNowMedia
- Gallery system for feed posts
- Image uploads with ordering
- Automatic WebP optimization
- Async image processing

#### RightNowLike & RightNowComment
- Social engagement tracking
- Unique constraints (one like/comment per user)
- Signal-based counter updates
- Timestamp-based ordering

### 2.4 Opportunity Matching

#### UnifiedJobPreference
- Long-term career preferences
- Role title and work arrangement
- Commitment type preferences
- Preference narrative
- Active/inactive status

#### LiveOpportunity
- Ephemeral "pings" to network
- Request types: MENTOR, HACKATHON, FREELANCE, COFOUNDER
- Expiration system
- Time-sensitive broadcasting

---

## 3. Team Management System

### 3.1 Team Model

**Core Fields:**
- `name`: Unique team name
- `slug`: Auto-generated URL identifier
- `mission`: Mission statement
- `team_type`: STARTUP, BUSINESS, PROJECT, HACKATHON, LEARNING, NON_PROFIT
- `leader`: Team creator/owner
- `roles_needed`: Description of required roles
- `telegram_link`: Group chat integration
- `status`: PENDING, APPROVED, REJECTED, ARCHIVED
- `is_recruiting`: Accepting new members flag
- `admin_feedback`: Admin review notes

**Smart Features:**
- Automatic slug generation with duplicate handling
- Unicode/emoji fallback handling
- Status workflow management
- Recruitment toggle system

### 3.2 Team Membership

**TeamMembership Model:**
- Unique team-user relationships
- Roles: LEADER, MEMBER
- Timestamp tracking
- Prevents duplicate memberships

**JoinRequest Model:**
- Application workflow system
- Status: PENDING, APPROVED, REJECTED
- Narrative pitch from applicant
- Unique constraint (one request per team)

### 3.3 Team Workflows

#### Team Creation Flow
1. User submits team proposal
2. Status set to PENDING
3. Admin reviews and approves/rejects
4. If approved, team becomes visible in Discover feed
5. Leader can toggle recruitment status

#### Join Application Flow
1. User discovers team in feed
2. Submits join request with narrative
3. Leader reviews applications in management console
4. Leader approves or rejects
5. If approved, membership created automatically
6. Team member count updates

#### Team Management Console
- Recruitment status toggle
- Member count display
- Pending request queue
- Application review interface
- Team edit capabilities

---

## 4. Messaging System

### 4.1 ChatMessage Model

**Core Fields:**
- `sender`: Message author
- `receiver`: Message recipient
- `body`: Text content
- `timestamp`: Auto-generated send time
- `is_read`: Read receipt tracking
- `attachment`: File upload support
- `is_edited`: Edit tracking
- `is_deleted`: Soft delete support

**Smart Properties:**
- `is_image`: Detects image attachments
- `filename`: Extracts attachment filename

**Performance Features:**
- Database indexes on sender/receiver pairs
- Timestamp-based ordering
- Thread-safe counter updates

### 4.2 Chat Hub Interface

**Layout:**
- Two-column responsive design
- Left sidebar: Conversation list
- Right panel: Active chat

**Conversation List:**
- Avatar display with fallback initials
- Unread message badges
- Last message preview
- Timestamp display
- Read receipt indicators
- Active conversation highlighting

**Active Chat Panel:**
- Partner profile header
- Message history with infinite scroll
- Sent/received message styling
- Attachment support (images, files)
- Edit/delete own messages
- Real-time timestamp display
- Mobile-optimized input area

**Input Features:**
- Auto-resizing textarea
- File attachment button
- Send button with loading states
- Edit mode with cancel
- Character limits

### 4.3 Message Actions

**Edit Message:**
- Inline edit mode activation
- Original text preservation
- Edit indicator display
- AJAX submission

**Delete Message:**
- Confirmation dialog
- Soft delete implementation
- Visual removal from chat

**Read Receipts:**
- Automatic read tracking
- Visual indicators (single/double check)
- Timestamp display

---

## 5. Network Discovery System (Nexus)

### 5.1 NetworkPost Model

**Purpose**: Professional collaboration and project opportunities

**Classification System:**
- **ProjectType**: STARTUP, SPECIFIC_PROJECT
- **Stage**: IDEATION, PROTOTYPING, VALIDATION, TRACTION, EXPANSION
- **Need**: COFOUNDER, COLLABORATOR, TEAM, ADVISOR, FEEDBACK

**Content Fields:**
- `headline`: Professional title
- `description`: Detailed project overview
- `project_type`: Nature and scope
- `project_stage`: Development maturity
- `need_type`: Partnership sought
- `looking_for`: Detailed requirements
- `is_active`: Feed visibility

**Intelligent Features:**
- Compatibility score calculation
- Stage-based matching
- Workflow stage advancement
- Urgency level determination
- Archive/reactivate functionality

### 5.2 Matching Intelligence

**Compatibility Scoring:**
- Project type compatibility
- Development stage alignment
- Skill requirement matching
- Geographic preference consideration
- Timeline synchronization

**Workflow Management:**
- Stage progression tracking
- Automatic advancement logic
- Archive and reactivate
- Urgency calculation based on stage

---

## 6. Opportunities System

### 6.1 Skill Taxonomy

**Skill Model:**
- Canonical skill names
- AI alias system for semantic matching
- Category-based organization
- Proficiency levels
- Trending skill flags
- AI-ready metadata structure

**AI Features:**
- Semantic skill matching (ReactJS == React)
- Vector embedding storage support
- Automatic categorization
- Trend analysis capabilities

### 6.2 JobPost Model

**Opportunity Types:**
- FULL_TIME, PART_TIME, INTERNSHIP
- CONTRACT, GIG, CHALLENGE
- ADVISORY, VOLUNTEER, COFOUNDER

**Content Fields:**
- `title`: Job title
- `description`: Mission narrative (Markdown)
- `job_type`: Opportunity classification
- `level`: Experience requirement (STUDENT to EXECUTIVE)
- `location`: Geographic location
- `is_remote`: Remote work flag
- `compensation_text`: Salary description
- `salary_min/max`: Salary range
- `deadline_date/text`: Deadline management
- `is_open_ended`: Rolling admission flag

**Challenge Mode:**
- `requires_challenge`: Proof-of-work requirement
- `challenge_description`: Task specification
- Portfolio project attachment requirement

**Source Attribution:**
- Internal user postings
- Company postings
- External job aggregation
- Official admin posts
- Source platform tracking

**AI Integration:**
- `required_skills`: Many-to-many skill relationships
- `ai_metadata`: JSON field for AI analysis
- `ai_match_score`: Quality scoring
- View and application counters

### 6.3 JobApplication Model

**Workflow Stages:**
- LINKED: Initial submission
- VIEWED: Recruiter reviewed
- SHORTLISTED: Passed screening
- INTERVIEW: Selected for interview
- REJECTED: Not suitable
- HIRED: Successfully placed

**Application Content:**
- `cover_note`: Personalized motivation
- `attached_project`: Portfolio proof-of-work
- `match_score`: AI compatibility score
- `ai_analysis`: Detailed AI reasoning

**Validation:**
- Challenge requirement enforcement
- Unique constraint (one application per job)
- Automatic application counting
- Status change tracking

---

## 7. Company Profile System

### 7.1 Company Model

**Core Identity:**
- Name and slug
- Logo and cover image
- Industry classification
- Location and size
- Website and social links
- Description and mission

**Company Services:**
- Service catalog
- Image gallery
- Description and pricing
- Custom ordering

**Company Milestones:**
- Year-based timeline
- Achievement tracking
- Display ordering

**Company News:**
- News and updates
- Publication dates
- Media attachments

**Company Members:**
- User associations
- Role-based access (OWNER, ADMIN, MEMBER)
- Active status tracking

---

## 8. User Authentication & Onboarding

### 8.1 Authentication System

**Supported Methods:**
- Email/password registration
- Google OAuth integration
- Phone number authentication
- Email verification (OTP)
- Password reset flows

**User Roles:**
- FOUNDER: Company founders
- VISIONARY: Project leaders
- EXPERT: Professional talent
- ADMIN: Platform administrators

### 8.2 Onboarding Flow

**Unified Onboarding:**
1. Role selection (FOUNDER/VISIONARY/EXPERT)
2. Basic profile information
3. Skills and interests
4. Portfolio setup (optional)
5. First "Right Now" post creation

**Profile Completion:**
- Progress tracking
- Guided setup wizard
- Optional vs required fields
- Skip functionality

---

## 9. UI/UX Implementation

### 9.1 Design System

**Typography:**
- Headings: Plus Jakarta Sans
- Body: Inter
- Custom letter-spacing for brand identity

**Color Palette:**
- Primary: CoreLink Blue (#0A66C2)
- Secondary: Indigo gradient
- Success: Emerald green
- Warning: Amber
- Error: Rose red
- Neutral: Slate gray scale

**Component Library:**
- Bento grid layouts
- Glass morphism effects
- Rounded corners (1rem-2.5rem)
- Subtle shadows and gradients
- Custom scrollbars
- Mobile-first responsive design

### 9.2 Navigation Architecture

**Desktop Navigation:**
- Left sidebar navigation (260-280px)
- Floating glass top bar (alternative)
- 5 main navigation items
- User actions in sidebar footer

**Mobile Navigation:**
- Fixed top bar with logo and menu
- Bottom tab navigation (5 items)
- Slide-up drawer menus
- Safe area handling for iOS

**Navigation Items:**
1. My Profile (Dashboard)
2. Discover (Nexus feed)
3. Updates (Right Now feed)
4. Opportunities (Job board)
5. Inbox (Messaging)

### 9.3 Dashboard Layouts

**Main Dashboard (Bento Grid):**
- Section 1: My Current Focus (full width)
- Section 2: Teams I Lead (half width)
- Section 3: Teams Joined (half width)
- Section 4: Applications & Opportunities (stacked)

**Team Management Console:**
- Left column: Status & Settings
- Right column: ATS/Applications
- Recruitment toggle
- Member overview
- Request queue

**Chat Hub:**
- Left: Conversation list
- Right: Active chat
- Mobile: Full-screen chat view
- Responsive breakpoints

### 9.4 Form Design

**Input Styles:**
- Clean, visible editor inputs
- Focus states with glow effects
- Error state styling
- Character limits
- Auto-resizing textareas

**Button Styles:**
- Primary: Gradient blue/indigo
- Secondary: White with border
- Action: Emerald/teal for teams
- Hover effects with transforms
- Loading states

---

## 10. Internationalization

### 10.1 Supported Languages
- English (en)
- Amharic (am)

### 10.2 Implementation
- Django i18n framework
- Template translation tags
- Language switcher in navigation
- RTL support ready
- Language-specific content

---

## 11. Performance Optimizations

### 11.1 Database Optimizations
- UUID primary keys for distributed systems
- Database indexes on frequently queried fields
- Denormalized counters for performance
- Select_related and prefetch_related usage
- Query optimization for feed loading

### 11.2 Image Processing
- Automatic WebP conversion
- Async image optimization
- Responsive image sizing
- Lazy loading implementation
- CDN-ready architecture

### 11.3 Caching Strategy
- Signal-based counter updates
- Metadata caching for external links
- Template fragment caching ready
- Static asset optimization

---

## 12. Security Features

### 12.1 Authentication Security
- CSRF protection on all forms
- Password hashing with bcrypt
- Session management
- Secure cookie settings

### 12.2 Authorization
- Login required decorators
- Owner/leader permission checks
- Role-based access control
- Company membership verification

### 12.3 Input Validation
- Form validation at multiple levels
- File type restrictions
- SQL injection prevention
- XSS protection via template escaping

---

## 13. Admin Operations

### 13.1 Operations Dashboard
- God-mode admin interface
- User management
- Content moderation
- Team approval workflow
- Company verification
- System analytics

### 13.2 Admin Features
- Bulk operations
- Status management
- Feedback system
- Assignment workflows
- Note-taking capabilities

---

## 14. Current Implementation Status

### 14.1 Fully Implemented Features
- ✅ User authentication and onboarding
- ✅ Unified profile system with modular components
- ✅ Right Now feed with social engagement
- ✅ Team creation and management
- ✅ Team join application workflow
- ✅ Real-time messaging system
- ✅ Network discovery feed (Nexus)
- ✅ Job opportunity posting
- ✅ Job application system
- ✅ Skill taxonomy
- ✅ Company profile system
- ✅ Internationalization (English/Amharic)
- ✅ Responsive mobile design
- ✅ Image optimization
- ✅ Admin operations interface

### 14.2 Partially Implemented Features
- 🔄 AI-powered matching (infrastructure ready, algorithm placeholder)
- 🔄 Challenge-based hiring (UI complete, verification pending)
- 🔄 External job aggregation (model ready, scraper pending)
- 🔄 Advanced analytics (tracking complete, visualization pending)
- 🔄 Email notifications (templates ready, sending pending)
- 🔄 Push notifications (infrastructure ready, integration pending)

### 14.3 Planned Future Features
- 📋 Video profile introductions
- 📋 Voice messaging
- 📋 Calendar integration
- 📋 Payment processing for premium features
- 📋 Advanced search filters
- 📋 Recommendation engine
- 📋 Mobile applications (React Native)
- 📋 API for third-party integrations

---

## 15. Technical Debt & Known Issues

### 15.1 Performance Considerations
- Large feed queries may need pagination optimization
- Image optimization should move to background tasks
- Database connection pooling for high traffic
- Caching layer implementation needed

### 15.2 Code Quality
- Some views exceed optimal length (refactoring needed)
- Duplicate code in similar views (DRY principle)
- Test coverage needs expansion
- API endpoint documentation needed

### 15.3 UX Improvements
- Empty states need more guidance
- Error messages could be more specific
- Onboarding flow could be more progressive
- Mobile navigation could be simplified

---

## 16. Deployment Architecture

### 16.1 Current Setup
- Development: SQLite database
- Production: PostgreSQL recommended
- Static files: Local filesystem
- Media files: Local filesystem (S3 ready)
- Web server: Django development server (Gunicorn recommended)
- Reverse proxy: Not configured (Nginx recommended)

### 16.2 Recommended Production Stack
- Web Server: Gunicorn
- Reverse Proxy: Nginx
- Database: PostgreSQL 14+
- Cache: Redis
- File Storage: AWS S3 or similar
- CDN: CloudFront or similar
- Monitoring: Sentry for error tracking
- Analytics: Google Analytics or similar

---

## 17. API Endpoints (Current)

### 17.1 Public APIs
- `GET /` - Landing page
- `GET /p/<slug>/` - Public profile
- `GET /company/<slug>/` - Company profile
- `GET /teams/<slug>/` - Team detail
- `GET /nexus/` - Network feed
- `GET /opportunities/` - Job board

### 17.2 Authenticated APIs
- `GET /workspace/` - Collaboration hub
- `GET /workspace/dashboard/` - User dashboard
- `GET /workspace/messages/` - Messaging hub
- `POST /workspace/messages/<user_id>/` - Send message
- `POST /teams/create/` - Create team
- `POST /teams/<slug>/join/` - Join team
- `POST /opportunities/<slug>/apply/` - Apply to job

### 17.3 AJAX Endpoints
- `POST /api/right-now/<id>/toggle-like/` - Like/unlike post
- `POST /api/right-now/<id>/add-comment/` - Add comment
- `POST /chat/delete/<id>/` - Delete message

---

## 18. Database Schema Summary

### 18.1 Core Tables
- `auth_user` - Django user model
- `profiles_userprofile` - Unified profile
- `profiles_profileheadline` - Professional identities
- `profiles_workexperience` - Work history
- `profiles_credential` - Certifications
- `profiles_skill` - Skill tracking
- `profiles_portfolioproject` - Portfolio projects
- `profiles_contentpost` - Content publishing
- `profiles_rightnowpost` - Feed posts
- `profiles_rightnowmedia` - Post media
- `profiles_rightnowlike` - Likes
- `profiles_rightnowcomment` - Comments

### 18.2 Collaboration Tables
- `workspace_team` - Teams
- `workspace_teammembership` - Team members
- `workspace_joinrequest` - Join applications
- `workspace_chatmessage` - Messages

### 18.3 Opportunity Tables
- `opportunities_skill` - Skill taxonomy
- `opportunities_jobpost` - Job postings
- `opportunities_jobapplication` - Applications

### 18.4 Network Tables
- `network_networkpost` - Collaboration posts

### 18.5 Company Tables
- `profiles_company` - Companies
- `profiles_companymember` - Company members
- `profiles_companyservice` - Services
- `profiles_companymilestone` - Milestones
- `profiles_companynews` - News

---

## 19. Monitoring & Analytics

### 19.1 Current Tracking
- Page views (Right Now posts)
- External link clicks
- Like counts
- Comment counts
- Application counts
- Message read receipts

### 19.2 User Engagement Metrics
- Daily active users
- Profile completion rates
- Team creation frequency
- Job posting activity
- Message volume
- Application submission rates

---

## 20. Conclusion

CoreLink represents a comprehensive professional networking platform with innovative features like the "Right Now" real-time feed, fluid portfolio architecture, and intelligent matching systems. The current implementation provides a solid foundation for scaling, with modular architecture that supports future enhancements.

The platform successfully addresses the core needs of:
- **Talent discovery** through skill-based matching
- **Team formation** through structured workflows
- **Opportunity matching** through AI-ready taxonomy
- **Professional networking** through real-time engagement
- **Career development** through portfolio showcasing

The implementation demonstrates strong technical fundamentals with room for optimization and feature expansion as the platform grows.

---

**Document End**
