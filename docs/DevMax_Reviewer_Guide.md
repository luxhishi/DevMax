# DevMax Reviewer Guide

## Purpose

This guide is a presenter-facing walkthrough of the current DevMax website.
It is written so that a reviewer, teammate, judge, or demo presenter can
study one document and understand what the product does, how the major
mechanics connect, and what to emphasize during a live demonstration.

## Product Summary

DevMax is a developer-focused forum platform built around community discussion.
The site combines community feeds, question solving, reputation mechanics,
predictive search, customizable user profiles, and moderation controls in a
single web experience.

The product language intentionally uses:

- "Subthreads" for topic communities, displayed as `d/<name>`
- "Aura" instead of karma or reputation
- "Achievements" instead of generic badges

## High-Level Navigation

The primary user-facing areas are:

- Home feed
- Trending feed
- Questions feed
- Individual subthreads
- Individual post detail pages
- User profiles
- Global search
- Notifications and account menu in the header

For superusers, there is also a moderation dashboard.

## Core Demo Story

If someone needs a clean presentation flow, this is the easiest sequence:

1. Show the Home feed and explain that it is the personalized feed.
2. Open Trending and explain that it is sitewide momentum, not the same as Home.
3. Open Questions and explain the solved workflow.
4. Enter a subthread and create or inspect a post.
5. Open a post detail page and show threaded comments, votes, and accepted answers.
6. Hover a username to show the Aura and achievement hover card.
7. Open a user profile to show profile photo, bio, Aura, achievements, and top posts.
8. Open the header search bar and show the predictive dropdown.
9. Open notifications and explain engagement events.
10. If relevant, show the superuser dashboard and manual moderation controls.

## Authentication and Onboarding

DevMax supports:

- Sign up
- Log in
- Log out
- Redirect to the Home feed immediately after successful signup

The login page also includes a direct CTA for new users:

- "New to DevMax? Sign up here"

This is important in demos because new-user navigation is now obvious from both
the header and the login screen itself.

## Header and Global Shell

The shared header includes:

- DevMax brand link
- Global search bar
- Notification bell for authenticated users
- Avatar menu for authenticated users
- Log in and Sign Up links for anonymous users

The header search bar supports predictive suggestions while typing. The
dropdown can show:

- Suggested searches
- Matching communities
- Matching user profiles
- Matching posts

Keyboard behavior includes:

- Arrow key navigation
- Enter to open a highlighted result
- Click-outside dismissal

The site also supports:

- Light and dark display mode
- A custom browser tab icon via `site-icon.png`

## Home Feed

Home is the personalized feed.

Behavior:

- For logged-in regular users, Home prioritizes posts from joined subthreads.
- For anonymous visitors and superusers, Home can show the wider feed.
- Ranking is not based only on raw lifetime upvotes.
- Recent content gets a freshness advantage, with engagement from votes and
  comments contributing to position.

What to say in a demo:

- Home is meant to feel relevant to the communities the user actually joined.
- It is distinct from Trending because it is community-first rather than
  sitewide momentum-first.

## Trending Feed

Trending is a sitewide momentum feed.

Behavior:

- It looks across the whole platform.
- It uses a recent activity window rather than lifetime popularity.
- It excludes auto-generated welcome posts.
- It requires a minimum amount of engagement before a post can trend.
- Manual superuser vote boosts affect trending, which is useful for demos.

What to say in a demo:

- Trending answers the question, "What is catching on across DevMax right now?"
- It is intentionally different from Home so the two feeds are not redundant.

## Questions Feed

The Questions feed is the structured Q and A layer of the product.

Entry points:

- Dedicated Questions page
- Ask Question modal
- Question-style posts also link to standard post detail pages

Available question controls:

- Sort by Newest
- Sort by Most Discussed
- Sort by Most Upvoted
- Filter by All
- Filter by Open
- Filter by Solved
- Filter by Unanswered

Question mechanics:

- Questions are stored as posts marked as question content.
- Solved questions show a clear solved state.
- Unanswered questions are explicitly detectable.
- Open questions have comments but no accepted answer.

## Solved Question Workflow

DevMax supports accepted answers.

Rules:

- Only the author of the question can mark a comment as solved.
- A superuser can also mark or unmark a solution.

Visible solved-state behavior:

- Solved pill on question cards
- Solved pill on the question detail page
- Accepted answer badge on the accepted comment
- Accepted answer promoted to the top area of the thread
- Unmark solved action on the accepted answer

What to say in a demo:

- DevMax treats Q and A content differently from general discussion.
- The solved flow gives the Questions feed a clear purpose separate from Home
  and Trending.

## Subthreads

Subthreads are the community containers for content.

Examples:

- `d/python`
- `d/django`
- `d/c++`

Current subthread mechanics:

- Create subthread from a floating modal
- Join subthread
- Leave subthread
- Delete subthread if the user manages it
- Member counts on the subthread page
- Suggested subthreads in side rails

Subthread pages provide:

- Community banner and description
- Joined state
- Create Post action
- Full feed of posts in that community

Important navigation detail:

- The visible `d/<subthread>` label on posts is clickable and routes back to
  the post's originating subthread.

## Post Creation and Display

Posts are the main discussion units.

Creation flow:

- Create Post opens in a floating modal
- Single-submit loading state prevents duplicate posts from spam clicking
- Users can add tags manually
- Tags are limited and normalized

Question-aware behavior:

- Question-style posts automatically include a `question` tag

Post card behavior:

- Shows subthread, author, time, title, content, tags, vote count, and comment count
- Achievement badge can appear in the top-right corner
- Post owner can delete their own post
- Superusers can also manage posts

Delete affordance refinement already present:

- Delete styling is neutral by default
- The trash icon stays visible
- Destructive color emphasis appears on hover/focus

## Tags

Tag behavior is part manual and part assisted.

Current rules:

- Users can provide tags when creating a post or asking a question
- Tags are normalized and limited
- Some posts can receive fallback tags based on context
- Question-style posts always receive the `question` tag
- Tags are clickable and route to search results

## Comments and Replies

DevMax supports threaded discussion.

Comment mechanics:

- Top-level comments
- Nested replies
- Collapse and expand for reply threads
- Inline reply forms
- Comment voting
- Comment deletion for managers

Discussion UI behavior:

- Root comments and replies have distinct visual treatment
- Reply counts are shown on collapsible threads
- Code formatting tools are available in composition flows

## Voting

Votes apply to both posts and comments.

Voting behavior:

- Upvote
- Downvote
- Toggle off by clicking the same vote again
- Logged-in user vote state is reflected visually
- Vote totals are synchronized after actions

Superuser moderation behavior:

- Manual post upvote boost
- Manual post downvote boost
- Manual comment upvote boost
- Manual comment downvote boost

These manual boosts are particularly useful in demos because they can be used
to surface content into Trending or trigger reputation milestones.

## Achievements

DevMax includes three achievement tiers.

Current tiers:

- Baby Steps
- Adept
- To The Stars

Award logic:

- Baby Steps at 5 upvotes on a post or comment
- Adept at 10 upvotes on a post or comment
- To The Stars at 15 or more upvotes on a post or comment

Badge display behavior:

- Badges can appear on posts
- Badges can appear on comments
- Badges appear in profile achievement summaries
- Badges appear in hover cards

Visual polish:

- Tier-specific glow styling
- Compact hover presentation on post cards
- Badge artwork sourced from local PNG assets

## Aura System

Aura is DevMax's reputation mechanic.

Current Aura rules:

- Each upvote gives +5 Aura
- Each response to a user's post or comment gives +10 Aura
- Baby Steps gives +50 Aura
- Adept gives +80 Aura
- To The Stars gives +150 Aura

Aura appears in:

- The user's profile header
- The profile stats card
- Username hover cards

What to say in a demo:

- Aura is the reputation total built from community reaction plus earned
  achievements.

## Achievement and Aura Placement

Profiles include an "Achievements" card that summarizes badge progress.

This card shows:

- Which achievements the user has earned
- How many times each one has been earned
- The Aura value tied to that tier

Post and comment surfaces show the single highest current tier reached by that
content item.

## Badge Notifications

When a post or comment crosses an achievement threshold, the owner receives a
notification.

Notification style:

- "You have been awarded the [badge name] badge! +[Aura amount] Aura >:)"

This turns achievements into an active feedback loop rather than a passive
profile-only system.

## Notifications

Authenticated users have an inbox in the header.

Notification sources include:

- New posts in relevant subthreads
- Comments on a user's posts
- Replies to a user's comments
- Achievement awards

Notification behavior:

- Unread badge count in the header
- Notification dropdown panel
- Notification links route to the relevant destination
- Notifications are marked read when opened

## User Profiles

Profiles now act as rich identity pages instead of simple account pages.

Main profile elements:

- Username
- Profile photo
- Editable bio
- Aura total
- Post count
- Comment count
- Subthread count
- Stats card
- Achievements card
- Top posts card

Activity tabs:

- Overview
- Posts
- Comments

Profile page layout details:

- Right sidebar has its own scroll behavior when content gets tall
- The layout is designed to keep stats and achievements visible without
  overwhelming the main activity column

## Profile Photo Flow

Users can upload a custom profile photo.

Current behavior:

- Hovering the avatar reveals an edit icon
- Clicking opens a floating modal
- Invalid file types show an error message
- Save action uses a loading state
- Updated avatar appears on the profile and in the header menu

Accepted image types:

- JPG
- JPEG
- PNG
- GIF
- WebP

## Bio Flow

Profiles support an editable bio.

Behavior:

- If no bio exists, the profile shows "No bio yet"
- The text itself is not the button
- "Edit bio" is the clickable action
- Bio editing happens in a floating modal

## Username Hover Cards

Hovering a username can show a quick profile preview card.

The hover card can surface:

- Username
- Aura total
- Achievement summary
- Profile photo
- Bio

This is useful in demos because it shows how DevMax surfaces reputation and
identity without forcing a full profile navigation every time.

## Search

DevMax supports:

- Full search results page
- Scope-aware search inside a subthread
- Predictive dropdown suggestions in the header

Search can find:

- Posts
- Subthreads
- User profiles
- Tags

Search results are organized into sections and tabs depending on context.

## Superuser and Moderation Tools

Superusers have access to a dedicated dashboard.

Dashboard surfaces:

- Platform-wide counts for users, subthreads, posts, comments, questions, and audit events
- Recent posts
- Recent comments
- Recent signups
- Recent subthreads
- Moderation audit log

Moderation controls available across the site include:

- Manual vote boosting
- Post deletion
- Comment deletion
- Subthread deletion
- Solved-question override ability

Audit logging captures moderation actions so they can be reviewed later.

## Visual and Interaction Polish

The site uses several UI refinements that are useful to mention in a review:

- Floating modal flows for creation and editing
- Loading states on important submit buttons
- Sticky rails and independent profile sidebar scroll
- Light and dark mode
- Predictive search dropdown
- Hover cards
- Distinct question-state pills
- Compact badge hover behavior

## Assets and Branding

Current static image assets include:

- Browser tab icon
- Three achievement badge PNGs

Tracked asset paths:

- `main/static/images/site-icon.png`
- `main/static/images/achievements/baby-steps.png`
- `main/static/images/achievements/adept.png`
- `main/static/images/achievements/to-the-stars.png`

These assets are part of the repository, so other collaborators receive them
when they pull the branch.

## Practical Demo Talking Points

If the presenter only has a short window, the strongest points are:

- DevMax separates Home, Trending, and Questions clearly instead of treating
  them as duplicates.
- Questions have a real solved mechanic rather than being just another feed.
- Reputation is productized as Aura plus visual achievements.
- Profiles are not static; they are customizable and tied to visible reputation.
- Search, hover cards, notifications, and badges make the site feel alive.
- Moderation and demo tooling exist through superuser controls and audit logs.

## Important Boundaries for the Presenter

The current demo should emphasize implemented mechanics and avoid overstating:

- The Share button is present in the UI, but it is not a core documented system.
- Footer links are mostly structural placeholders rather than a finished info architecture.

## Final Summary

DevMax is currently best described as a developer forum platform with:

- Personalized feeds
- Sitewide trending discovery
- Dedicated Q and A solving
- Community subthreads
- Threaded discussion
- Votes and reputation
- Achievement-driven feedback
- Search and hover discovery
- Customizable profiles
- Moderation oversight

Anyone presenting the website should frame it as a discussion platform with
clear identity, clear progression mechanics, and strong separation between
discussion, discovery, and problem-solving.
