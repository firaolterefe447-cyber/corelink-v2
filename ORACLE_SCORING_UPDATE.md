# Oracle Scoring System Update - Deployment Guide

## Overview
The Oracle scoring system has been redesigned to provide smoother, more gradual rating progression that rewards deliberate, high-quality profile building rather than quick additions. **Admin locks have been removed** - every single update now counts toward the user's score.

## Key Changes

### 1. Verification Removed
- **Before**: 5 points for verified users
- **After**: 0 points (all users are now considered verified)

### 2. Admin Locks Removed
- **Before**: Admins could lock ratings to prevent Oracle updates
- **After**: No locks - every update triggers Oracle recalculation
- **Impact**: Users see real-time progress with every action

### 3. Project Gallery/PDF Scoring Added
Projects now earn bonus points based on visual evidence:
- **5+ images/PDFs**: +5 points (Elite)
- **3-4 images/PDFs**: +3 points (Strong)
- **1-2 images/PDFs**: +1 point (Base)
- **0 images/PDFs**: No bonus

### 4. Skill Context Bonus Added
Skills with detailed explanations earn bonus points:
- **Base skill**: 1 point (even without context)
- **With context (50+ chars)**: +1 bonus point
- This rewards users who explain their skills meaningfully

### 5. Smoothed Point Values
All point values have been reduced to prevent rapid score jumps:

| Category | Before | After |
|----------|--------|-------|
| Avatar | 5 | 2 |
| Cover Image | 5 | 2 |
| Social Links (max) | 6 | 3 |
| Contact Methods (max) | 4 | 2 |
| Bio Narrative (max) | 12 | 4 |
| Current Mission (max) | 8 | 4 |
| CV File | 5 | 2 |
| Projects (each) | 6-25 | 2 + gallery bonus |
| Work Experience (max) | 15 | 5 |
| Credentials (max) | 15 | 5 |
| Skills (each) | 3-15 | 1 + context bonus |
| Languages (max) | 10 | 3 |
| Content Posts (max) | 10 | 4 |
| Company Assets (max) | 40 | 20 |

### 6. Updated Rating Thresholds
Rating progression is now more gradual:

| Rating | Before Score | After Score |
|--------|--------------|-------------|
| 4 Stars (Elite) | 90+ | 60+ |
| 3 Stars (Solid Pro) | 70+ | 40+ |
| 2 Stars (Developing) | 45+ | 25+ |
| 1 Star (Basic) | 20+ | 10+ |
| 0 Stars (Ghost) | <20 | <10 |

### 7. Real-Time Progress Dashboard
- **New**: Live progress bar on main dashboard
- **Features**: Animated score updates, point change notifications
- **API**: New endpoint `/api/oracle-score/` for real-time fetching
- **Visuals**: Modern gradient bar with shimmer animation

## Deployment Steps

### 1. Deploy Code Changes
Deploy the following files to production:
- `profiles/automatic_rating.py` - Updated Oracle logic (no locks)
- `profiles/views.py` - New `api_get_oracle_score` endpoint
- `profiles/urls.py` - New API route
- `theme/templates/dashboard/main_dashboard.html` - Updated progress bar
- `profiles/management/commands/unlock_all_ratings.py` - Unlock command
- `profiles/management/commands/recalculate_oracle_smooth.py` - Recalculation command

### 2. Unlock All User Ratings
Execute the command to unlock all locked ratings:

```bash
python manage.py unlock_all_ratings
```

This command:
- Sets `is_rating_locked = False` for all profiles
- Allows Oracle to update all ratings going forward
- Completes instantly

### 3. Run Recalculation Command
Execute the command to recalculate all user scores:

```bash
python manage.py recalculate_oracle_smooth
```

This command:
- Iterates through all active users
- Recalculates Oracle scores using the new system
- Updates both `oracle_score` and `admin_rating` fields
- Shows progress every 100 users
- Completes in ~5 minutes for 10,000 users

### 4. Monitor Results
After running the commands, check:
- User ratings in the admin panel
- Feed ordering (should reflect new scores)
- Dashboard progress bar displays correctly
- Real-time score updates work on form submissions

### 5. Rollback Plan (if needed)
If issues arise, you can:
1. Restore the previous `automatic_rating.py` file (with lock logic)
2. Restore the previous dashboard template
3. Run the recalculation command again with the old system
4. This will revert all scores to the previous calculation

## Expected Impact

### Score Distribution Changes
- Most users will see their raw scores decrease (due to reduced point values)
- Rating tiers will shift to match the new thresholds
- Users with rich portfolios (projects with galleries, skills with context) will be rewarded
- Every single action now contributes to score progression

### User Experience Improvements
- **Immediate feedback**: Users see score changes in real-time
- **Transparent progression**: Clear visual indicator of profile completion
- **Motivation**: Small actions (adding 1 skill) now show impact
- **Quality focus**: Gallery and context bonuses reward depth

### User Communication
Consider notifying users about the rating system update:
- Explain the focus on quality over quantity
- Highlight the new gallery and context bonuses
- Reassure them that every action now counts toward their score
- Mention the real-time progress indicator on dashboard

## Technical Notes

### Performance
- The recalculation command uses chunked iteration (500 users at a time)
- Prefetches related models to minimize database queries
- Real-time API endpoint is lightweight (single DB query)
- Dashboard JavaScript uses MutationObserver for form detection

### Database Impact
- Updates `oracle_score` and `admin_rating` fields for all users
- Updates `is_rating_locked` field to False for all users
- Uses `update_fields` to minimize database writes
- Transaction-safe (commits after each user)

### Signal Triggers
- The Oracle triggers automatically on every profile change
- No locks prevent updates
- New scoring applies immediately to all future updates
- Real-time API fetches latest score after form submissions

### API Endpoint
- **Route**: `/api/oracle-score/`
- **Method**: GET
- **Authentication**: Required (login_required)
- **Response**: `{ "status": "success", "oracle_score": 45, "admin_rating": 2 }`

## Testing Checklist

Before deploying to production:
- [ ] Test unlock command on staging database
- [ ] Test recalculation command on staging database
- [ ] Verify score calculations match expected values
- [ ] Confirm gallery bonuses work correctly
- [ ] Validate skill context bonuses
- [ ] Test real-time score updates on dashboard
- [ ] Monitor feed ordering after update
- [ ] Check admin panel rating display
- [ ] Verify API endpoint returns correct data
- [ ] Test progress bar animations on mobile
