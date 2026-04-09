from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import resolve, reverse

from .models import AdminAuditLog, Comment, Notification, Post, Subthread, SubthreadMembership, Tag, UserPreference, Vote


class RoutingTests(TestCase):
    TEST_STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

    def test_root_redirects_to_main_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("main:index"))

    def test_main_named_routes_reverse_to_main_prefix(self):
        self.assertEqual(reverse("main:index"), "/main/")
        self.assertEqual(reverse("main:questions"), "/main/questions/")
        self.assertEqual(reverse("main:superuser_dashboard"), "/main/superuser/")
        self.assertEqual(reverse("main:ask_question"), "/main/questions/ask/")
        self.assertEqual(reverse("main:search"), "/main/search/")
        self.assertEqual(reverse("main:adjust_post_votes", args=[42]), "/main/admin/post/42/votes/")
        self.assertEqual(reverse("main:adjust_comment_votes", args=[42]), "/main/admin/comment/42/votes/")
        self.assertEqual(reverse("main:delete_comment", args=[42]), "/main/comment/42/delete/")
        self.assertEqual(reverse("main:update_display_mode"), "/main/display-mode/")
        self.assertEqual(reverse("main:login"), "/main/login/")
        self.assertEqual(reverse("main:profile"), "/main/profile/")
        self.assertEqual(reverse("main:update_profile_photo"), "/main/profile/photo/")
        self.assertEqual(reverse("main:update_profile_bio"), "/main/profile/bio/")
        self.assertEqual(reverse("main:user_hover_card", args=["alice"]), "/main/u/alice/hover-card/")
        self.assertEqual(reverse("main:user_profile", args=["alice"]), "/main/u/alice/")
        self.assertEqual(reverse("main:subthread_detail", args=["python"]), "/main/d/python/")
        self.assertEqual(reverse("main:join_subthread", args=["python"]), "/main/d/python/join/")
        self.assertEqual(reverse("main:leave_subthread", args=["python"]), "/main/d/python/leave/")
        self.assertEqual(reverse("main:delete_subthread", args=["python"]), "/main/d/python/delete/")
        self.assertEqual(reverse("main:create_post", args=["python"]), "/main/d/python/create-post/")
        self.assertEqual(reverse("main:delete_post", kwargs={"name": "python", "post_id": 42}), "/main/d/python/42/delete/")
        self.assertEqual(reverse("main:post_detail", kwargs={"name": "python", "post_id": 42}), "/main/d/python/42/")

    def test_main_index_route_resolves(self):
        self.assertEqual(resolve("/main/").view_name, "main:index")

    def test_questions_route_resolves(self):
        self.assertEqual(resolve("/main/questions/").view_name, "main:questions")

    def test_superuser_dashboard_requires_superuser(self):
        user = User.objects.create_user(username="regularuser", password="testpass123")
        self.client.force_login(user)

        response = self.client.get(reverse("main:superuser_dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("main:profile"))
        self.assertEqual(response.status_code, 302)

    def test_profile_route_redirects_to_username_url(self):
        user = User.objects.create_user(username="profileowner", password="testpass123")
        self.client.force_login(user)

        response = self.client.get(reverse("main:profile"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("main:user_profile", args=[user.username]))

    def test_anonymous_pages_default_to_light_mode(self):
        response = self.client.get(reverse("main:index"))
        self.assertContains(response, 'data-display-mode="light"')

    def test_display_mode_update_is_saved_per_user(self):
        user = User.objects.create_user(username="carol", password="testpass123")
        self.client.force_login(user)

        response = self.client.post(reverse("main:update_display_mode"), {"display_mode": "dark"})

        self.assertEqual(response.status_code, 200)
        preference = UserPreference.objects.get(user=user)
        self.assertEqual(preference.display_mode, "dark")

        response = self.client.get(reverse("main:index"))
        self.assertContains(response, 'data-display-mode="dark"')

    def test_logout_returns_to_light_mode_for_anonymous_state(self):
        user = User.objects.create_user(username="dana", password="testpass123")
        UserPreference.objects.create(user=user, display_mode="dark")
        self.client.force_login(user)

        response = self.client.get(reverse("main:logout"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-display-mode="light"')

    def test_create_post_route_accepts_post(self):
        user = User.objects.create_user(username="alice", password="testpass123")
        subthread = Subthread.objects.create(name="python", description="Python", created_by=user)

        self.client.login(username="alice", password="testpass123")
        response = self.client.post(
            reverse("main:create_post", args=[subthread.name]),
            {"title": "Hello", "content": "Routing works"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("main:subthread_detail", args=[subthread.name]))

    def test_create_post_persists_user_tags_and_renders_clickable_tag_search(self):
        user = User.objects.create_user(username="tagcreator", password="testpass123")
        subthread = Subthread.objects.create(name="tagged-python", description="Python", created_by=user)

        self.client.force_login(user)
        self.client.post(
            reverse("main:create_post", args=[subthread.name]),
            {
                "title": "Factories and fixtures",
                "content": "Looking for setup patterns.",
                "tags": "pytest, fixtures, testing",
            },
        )

        post = Post.objects.get(title="Factories and fixtures")
        self.assertCountEqual(
            list(post.tags.values_list("name", flat=True)),
            ["pytest", "fixtures", "testing"],
        )

        response = self.client.get(reverse("main:subthread_detail", args=[subthread.name]))
        self.assertContains(response, 'href="/main/search/?q=pytest&amp;tab=posts&amp;scope=tagged-python"')
        self.assertContains(response, "pytest")

    def test_create_post_auto_adds_question_tag_for_question_style_posts(self):
        user = User.objects.create_user(username="questiontagger", password="testpass123")
        subthread = Subthread.objects.create(name="question-tags", description="Questions", created_by=user)

        self.client.force_login(user)
        self.client.post(
            reverse("main:create_post", args=[subthread.name]),
            {
                "title": "How do I structure Django forms?",
                "content": "I am trying to clean up a complex form flow.",
                "tags": "django, forms, validation",
            },
        )

        post = Post.objects.get(title="How do I structure Django forms?")
        self.assertCountEqual(
            list(post.tags.values_list("name", flat=True)),
            ["question", "django", "forms", "validation"],
        )

    def test_search_posts_by_tag_matches_real_post_tags(self):
        user = User.objects.create_user(username="tagsearch", password="testpass123")
        subthread = Subthread.objects.create(name="search-tags", description="Tags", created_by=user)
        post = Post.objects.create(title="Untitled note", content="No keyword overlap here.", subthread=subthread, author=user)
        tag = Tag.objects.create(name="orm")
        post.tags.add(tag)

        response = self.client.get(f"{reverse('main:search')}?q=orm&tab=posts")

        self.assertContains(response, "Untitled note")

    def test_home_feed_shows_posts_from_joined_subthreads(self):
        owner = User.objects.create_user(username="feedowner", password="testpass123")
        viewer = User.objects.create_user(username="feedviewer", password="testpass123")
        joined_subthread = Subthread.objects.create(name="joined-feed", description="Joined", created_by=owner)
        other_subthread = Subthread.objects.create(name="other-feed", description="Other", created_by=owner)
        Post.objects.create(title="Joined post", content="Content", subthread=joined_subthread, author=owner)
        Post.objects.create(title="Other post", content="Content", subthread=other_subthread, author=owner)
        SubthreadMembership.objects.create(user=viewer, subthread=joined_subthread)

        self.client.force_login(viewer)
        response = self.client.get(reverse("main:index"))

        self.assertContains(response, "Joined post")
        self.assertNotContains(response, "Other post")

    def test_superuser_home_feed_shows_all_posts_without_memberships(self):
        owner = User.objects.create_user(username="feedcreator", password="testpass123")
        superuser = User.objects.create_superuser(username="feedsuper", email="feedsuper@example.com", password="testpass123")
        first_subthread = Subthread.objects.create(name="global-one", description="One", created_by=owner)
        second_subthread = Subthread.objects.create(name="global-two", description="Two", created_by=owner)
        Post.objects.create(title="First global post", content="Content", subthread=first_subthread, author=owner)
        Post.objects.create(title="Second global post", content="Content", subthread=second_subthread, author=owner)

        self.client.force_login(superuser)
        response = self.client.get(reverse("main:index"))

        self.assertContains(response, "First global post")
        self.assertContains(response, "Second global post")
        self.assertFalse(response.context["personalized_home_feed"])

    def test_questions_page_filters_to_question_style_posts(self):
        owner = User.objects.create_user(username="questionowner", password="testpass123")
        subthread = Subthread.objects.create(name="questions", description="Questions", created_by=owner)
        Post.objects.create(title="How do I loop in Python?", content="Need help", subthread=subthread, author=owner)
        Post.objects.create(title="Python release notes", content="Version update", subthread=subthread, author=owner)

        response = self.client.get(reverse("main:questions"))

        self.assertContains(response, "How do I loop in Python?")
        self.assertNotContains(response, "Python release notes")
        self.assertContains(response, "Newest Questions")
        self.assertContains(response, "Questions")

    def test_questions_page_shows_ask_question_button_for_logged_in_users(self):
        owner = User.objects.create_user(username="askbutton", password="testpass123")
        Subthread.objects.create(name="django", description="Django", created_by=owner)

        self.client.force_login(owner)
        response = self.client.get(reverse("main:questions"))

        self.assertContains(response, 'id="ask-question-btn"')
        self.assertContains(response, reverse("main:ask_question"))
        self.assertContains(response, "Start a new question")

    def test_ask_question_creates_question_post_and_redirects_to_detail(self):
        owner = User.objects.create_user(username="asker", password="testpass123")
        subthread = Subthread.objects.create(name="python", description="Python", created_by=owner)

        self.client.force_login(owner)
        response = self.client.post(
            reverse("main:ask_question"),
            {
                "subthread_id": subthread.id,
                "title": "How do I test Django views?",
                "content": "I need help writing tests for a view.",
                "tags": "django, testing",
            },
        )

        post = Post.objects.get(title="How do I test Django views?")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(post.is_question)
        self.assertEqual(post.author, owner)
        self.assertEqual(post.subthread, subthread)
        self.assertCountEqual(list(post.tags.values_list("name", flat=True)), ["question", "django", "testing"])
        self.assertEqual(
            response.headers["Location"],
            reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id}),
        )

    def test_explicit_question_posts_show_on_questions_page_without_question_mark(self):
        owner = User.objects.create_user(username="questionflag", password="testpass123")
        subthread = Subthread.objects.create(name="testing", description="Testing", created_by=owner)
        Post.objects.create(
            title="Need help with fixtures",
            content="This should still appear in questions.",
            subthread=subthread,
            author=owner,
            is_question=True,
        )

        response = self.client.get(reverse("main:questions"))

        self.assertContains(response, "Need help with fixtures")

    def test_questions_page_unanswered_filter_only_shows_zero_comment_questions(self):
        owner = User.objects.create_user(username="unansweredowner", password="testpass123")
        subthread = Subthread.objects.create(name="unanswered", description="Unanswered", created_by=owner)
        unanswered = Post.objects.create(title="What is Django ORM?", content="Question body", subthread=subthread, author=owner)
        answered = Post.objects.create(title="How do signals work?", content="Question body", subthread=subthread, author=owner)
        Comment.objects.create(post=answered, author=owner, content="An answer-like comment")

        response = self.client.get(f"{reverse('main:questions')}?sort=unanswered")

        self.assertContains(response, unanswered.title)
        self.assertNotContains(response, answered.title)
        self.assertContains(response, "Unanswered Questions")

    def test_create_subthread_auto_joins_creator(self):
        user = User.objects.create_user(username="builder", password="testpass123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("main:create_subthread"),
            {"name": "cplusplus", "description": "C++ discussions"},
        )

        subthread = Subthread.objects.get(name="cplusplus")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SubthreadMembership.objects.filter(user=user, subthread=subthread).exists())
        self.assertEqual(subthread.members, 1)

    def test_join_subthread_creates_membership_and_renders_joined_state(self):
        owner = User.objects.create_user(username="owner", password="testpass123")
        viewer = User.objects.create_user(username="viewer", password="testpass123")
        subthread = Subthread.objects.create(name="django", description="Django", created_by=owner)

        self.client.force_login(viewer)
        response = self.client.post(
            reverse("main:join_subthread", args=[subthread.name]),
            {"next": reverse("main:subthread_detail", args=[subthread.name])},
            follow=True,
        )

        subthread.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SubthreadMembership.objects.filter(user=viewer, subthread=subthread).exists())
        self.assertEqual(subthread.members, 2)
        self.assertTrue(response.context["subthread_is_joined"])

    def test_sidebar_and_suggestions_use_real_memberships(self):
        owner = User.objects.create_user(username="owner2", password="testpass123")
        viewer = User.objects.create_user(username="viewer2", password="testpass123")
        joined = Subthread.objects.create(name="joined-club", description="Joined club", created_by=owner)
        suggested = Subthread.objects.create(name="suggest-me", description="Suggest me", created_by=owner)
        SubthreadMembership.objects.create(user=viewer, subthread=joined)

        self.client.force_login(viewer)
        response = self.client.get(reverse("main:index"))

        self.assertContains(response, f'd/{joined.name}')
        self.assertContains(response, f'action="{reverse("main:join_subthread", args=[suggested.name])}"')
        self.assertContains(response, f'name="next" value="{reverse("main:index")}"')

    def test_leave_subthread_removes_membership_and_restores_join_state(self):
        owner = User.objects.create_user(username="owner3", password="testpass123")
        viewer = User.objects.create_user(username="viewer3", password="testpass123")
        subthread = Subthread.objects.create(name="leave-me", description="Leave me", created_by=owner)
        SubthreadMembership.objects.create(user=viewer, subthread=subthread)
        subthread.members = 2
        subthread.save(update_fields=["members"])

        self.client.force_login(viewer)
        response = self.client.post(
            reverse("main:leave_subthread", args=[subthread.name]),
            {"next": reverse("main:subthread_detail", args=[subthread.name])},
            follow=True,
        )

        subthread.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SubthreadMembership.objects.filter(user=viewer, subthread=subthread).exists())
        self.assertEqual(subthread.members, 1)
        self.assertFalse(response.context["subthread_is_joined"])
        self.assertContains(response, f'action="{reverse("main:join_subthread", args=[subthread.name])}"')

    def test_new_post_notifies_joined_members_and_subthread_creator(self):
        owner = User.objects.create_user(username="notifyowner", password="testpass123")
        member = User.objects.create_user(username="notifymember", password="testpass123")
        author = User.objects.create_user(username="notifyposter", password="testpass123")
        subthread = Subthread.objects.create(name="notify-subthread", description="Notify", created_by=owner)
        SubthreadMembership.objects.create(user=member, subthread=subthread)

        post = Post.objects.create(title="Fresh post", content="New content", subthread=subthread, author=author)

        self.assertTrue(
            Notification.objects.filter(
                user=owner,
                notification_type=Notification.TYPE_SUBTHREAD_POST,
                post=post,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=member,
                notification_type=Notification.TYPE_SUBTHREAD_POST,
                post=post,
            ).exists()
        )
        self.assertFalse(Notification.objects.filter(user=author, post=post).exists())

    def test_comment_and_reply_notifications_are_created(self):
        owner = User.objects.create_user(username="commentowner", password="testpass123")
        commenter = User.objects.create_user(username="commenter", password="testpass123")
        replier = User.objects.create_user(username="replier", password="testpass123")
        subthread = Subthread.objects.create(name="notify-comments", description="Notify comments", created_by=owner)
        post = Post.objects.create(title="Post title", content="Post body", subthread=subthread, author=owner)

        comment = Comment.objects.create(post=post, author=commenter, content="First comment")
        reply = Comment.objects.create(post=post, author=replier, content="Reply comment", parent=comment)

        self.assertTrue(
            Notification.objects.filter(
                user=owner,
                notification_type=Notification.TYPE_POST_COMMENT,
                comment=comment,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=commenter,
                notification_type=Notification.TYPE_COMMENT_REPLY,
                comment=reply,
            ).exists()
        )

    def test_notification_bell_renders_and_mark_read_endpoint_clears_unread(self):
        owner = User.objects.create_user(username="bellowner", password="testpass123")
        actor = User.objects.create_user(username="bellactor", password="testpass123")
        subthread = Subthread.objects.create(name="bell-subthread", description="Bell", created_by=owner)
        post = Post.objects.create(title="Bell post", content="Body", subthread=subthread, author=actor)
        notification = Notification.objects.filter(user=owner, post=post).first()

        self.client.force_login(owner)
        response = self.client.get(reverse("main:index"))

        self.assertIsNotNone(notification)
        self.assertContains(response, 'id="notification-menu-button"')
        self.assertContains(response, 'id="notification-badge"')
        self.assertContains(response, notification.message)

        read_response = self.client.post(reverse("main:mark_notifications_read"))

        notification.refresh_from_db()
        self.assertEqual(read_response.status_code, 200)
        self.assertTrue(notification.is_read)

    def test_post_badge_threshold_creates_achievement_notification(self):
        author = User.objects.create_user(username="badgeauthor", password="testpass123")
        voter = User.objects.create_user(username="postvoter", password="testpass123")
        subthread = Subthread.objects.create(name="badge-notify-post", description="Badges", created_by=author)
        post = Post.objects.create(
            title="Threshold post",
            content="Content",
            subthread=subthread,
            author=author,
            manual_upvotes=4,
            upvotes=4,
        )

        self.client.force_login(voter)
        response = self.client.post(reverse("main:vote_post", args=[post.id]), {"vote_type": "up"})

        notification = Notification.objects.get(
            user=author,
            notification_type=Notification.TYPE_ACHIEVEMENT_BEGINNER,
            post=post,
            comment__isnull=True,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(notification.message, "You have been awarded the Baby Steps badge! +50 Aura >:)")
        self.assertEqual(
            notification.target_url,
            reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id}),
        )

    def test_comment_badge_threshold_creates_achievement_notification_with_comment_anchor(self):
        post_author = User.objects.create_user(username="commentpostowner", password="testpass123")
        comment_author = User.objects.create_user(username="commentbadgeowner", password="testpass123")
        voter = User.objects.create_user(username="commentvoter", password="testpass123")
        subthread = Subthread.objects.create(name="badge-notify-comment", description="Badges", created_by=post_author)
        post = Post.objects.create(title="Parent post", content="Body", subthread=subthread, author=post_author)
        comment = Comment.objects.create(
            post=post,
            author=comment_author,
            content="Helpful comment",
            manual_upvotes=9,
            upvotes=9,
        )

        self.client.force_login(voter)
        response = self.client.post(reverse("main:vote_comment", args=[comment.id]), {"vote_type": "up"})

        notification = Notification.objects.get(
            user=comment_author,
            notification_type=Notification.TYPE_ACHIEVEMENT_INTERMEDIATE,
            post=post,
            comment=comment,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(notification.message, "You have been awarded the Adept badge! +80 Aura >:)")
        self.assertEqual(
            notification.target_url,
            f"{reverse('main:post_detail', kwargs={'name': subthread.name, 'post_id': post.id})}#comments",
        )

    def test_empty_subthread_gets_real_welcome_post(self):
        user = User.objects.create_user(username="bob", password="testpass123")
        subthread = Subthread.objects.create(name="routing-test", description="Routing", created_by=user)

        response = self.client.get(reverse("main:subthread_detail", args=[subthread.name]))

        self.assertEqual(response.status_code, 200)
        welcome_post = Post.objects.get(subthread=subthread, title=f"Welcome to d/{subthread.name}!")
        self.assertContains(response, reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": welcome_post.id}))

    def test_post_detail_back_link_uses_subthread_context(self):
        user = User.objects.create_user(username="erin", password="testpass123")
        subthread = Subthread.objects.create(name="webdev", description="Webdev", created_by=user)
        post = Post.objects.create(title="Best Tailwind Plugins?", content="Content", subthread=subthread, author=user)

        response = self.client.get(
            f"{reverse('main:post_detail', kwargs={'name': subthread.name, 'post_id': post.id})}?from_subthread={subthread.name}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{reverse("main:subthread_detail", args=[subthread.name])}"')

    def test_subthread_posts_link_back_to_same_subthread(self):
        user = User.objects.create_user(username="frank", password="testpass123")
        subthread = Subthread.objects.create(name="frontend", description="Frontend", created_by=user)
        post = Post.objects.create(title="A post", content="Content", subthread=subthread, author=user)

        response = self.client.get(reverse("main:subthread_detail", args=[subthread.name]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f"{reverse('main:post_detail', kwargs={'name': subthread.name, 'post_id': post.id})}?from_subthread={subthread.name}",
        )

    def test_feed_comment_link_opens_post_detail_comments_section(self):
        user = User.objects.create_user(username="faye", password="testpass123")
        subthread = Subthread.objects.create(name="comment-link", description="Links", created_by=user)
        post = Post.objects.create(title="Comment target", content="Content", subthread=subthread, author=user)

        self.client.force_login(user)
        response = self.client.get(reverse("main:index"))

        self.assertContains(
            response,
            f'{reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id})}#comments',
        )

    def test_global_search_returns_matching_subthreads_and_posts(self):
        user = User.objects.create_user(username="soren", password="testpass123")
        matching_subthread = Subthread.objects.create(name="django", description="All things Django", created_by=user)
        other_subthread = Subthread.objects.create(name="python", description="General Python", created_by=user)
        Post.objects.create(title="Django forms help", content="Need help with ModelForm", subthread=matching_subthread, author=user)
        Post.objects.create(title="Loop question", content="Python loops", subthread=other_subthread, author=user)

        response = self.client.get(f"{reverse('main:search')}?q=django")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["search_scope_name"], "")
        self.assertContains(response, 'action="/main/search/"')
        self.assertContains(response, 'Results for "django"')
        self.assertContains(response, "d/django")
        self.assertContains(response, "Django forms help")
        self.assertNotContains(response, "Loop question")

    def test_global_search_returns_matching_profiles(self):
        profile_user = User.objects.create_user(username="ryangiray", password="testpass123")

        response = self.client.get(f"{reverse('main:search')}?q=ryan")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["profile_total"], 1)
        self.assertContains(response, "Profiles")
        self.assertContains(response, f'href="{reverse("main:user_profile", args=[profile_user.username])}"')
        self.assertContains(response, f"u/{profile_user.username}")

    def test_global_search_supports_u_prefix_for_profiles(self):
        profile_user = User.objects.create_user(username="lucis", password="testpass123")

        response = self.client.get(f"{reverse('main:search')}?q=u/{profile_user.username}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["profile_total"], 1)
        self.assertContains(response, f'href="{reverse("main:user_profile", args=[profile_user.username])}"')

    def test_global_search_renders_all_tabs(self):
        user = User.objects.create_user(username="tabuser", password="testpass123")
        response = self.client.get(f"{reverse('main:search')}?q={user.username}")

        self.assertEqual(response.context["active_search_tab"], "all")
        self.assertEqual([tab["id"] for tab in response.context["search_tabs"]], ["all", "posts", "subthreads", "users"])
        self.assertContains(response, ">All<")
        self.assertContains(response, ">Posts<")
        self.assertContains(response, ">Subthreads<")
        self.assertContains(response, ">Users<")

    def test_search_posts_tab_only_shows_post_results(self):
        profile_user = User.objects.create_user(username="djangofan", password="testpass123")
        subthread = Subthread.objects.create(name="django", description="Django", created_by=profile_user)
        Post.objects.create(title="Django post", content="forms", subthread=subthread, author=profile_user)

        response = self.client.get(f"{reverse('main:search')}?q=django&tab=posts")

        self.assertEqual(response.context["active_search_tab"], "posts")
        self.assertContains(response, "Django post")
        self.assertNotContains(response, 'class="search-profile-card"')
        self.assertNotContains(response, "No subthreads matched your search yet.")

    def test_search_users_tab_only_shows_profile_results(self):
        profile_user = User.objects.create_user(username="devryan", password="testpass123")
        subthread = Subthread.objects.create(name="dev", description="Dev", created_by=profile_user)
        Post.objects.create(title="Dev note", content="General dev content", subthread=subthread, author=profile_user)

        response = self.client.get(f"{reverse('main:search')}?q=dev&tab=users")

        self.assertEqual(response.context["active_search_tab"], "users")
        self.assertContains(response, f"u/{profile_user.username}")
        self.assertNotContains(response, "Dev note")
        self.assertNotContains(response, "No subthreads matched your search yet.")

    def test_subthread_detail_header_search_shows_scope_chip(self):
        user = User.objects.create_user(username="tess", password="testpass123")
        subthread = Subthread.objects.create(name="django", description="Django", created_by=user)

        response = self.client.get(reverse("main:subthread_detail", args=[subthread.name]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="scope" value="django"')
        self.assertContains(response, "in d/django")
        self.assertContains(response, "Search in d/django")

    def test_scoped_search_limits_results_to_selected_subthread(self):
        user = User.objects.create_user(username="uma", password="testpass123")
        django = Subthread.objects.create(name="django", description="Django", created_by=user)
        python = Subthread.objects.create(name="python", description="Python", created_by=user)
        Post.objects.create(title="ORM indexing", content="query optimization", subthread=django, author=user)
        Post.objects.create(title="ORM indexing", content="sqlite question", subthread=python, author=user)

        response = self.client.get(f"{reverse('main:search')}?q=ORM&scope=django")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["search_scope_name"], "django")
        self.assertContains(response, 'Results for "ORM"')
        self.assertContains(response, 'name="scope" value="django"')
        self.assertContains(response, "Search in d/django")
        self.assertContains(response, "query optimization")
        self.assertNotContains(response, "sqlite question")

    def test_scoped_search_only_offers_posts_tab(self):
        user = User.objects.create_user(username="scopeuser", password="testpass123")
        subthread = Subthread.objects.create(name="django", description="Django", created_by=user)
        Post.objects.create(title="Scoped result", content="Content", subthread=subthread, author=user)

        response = self.client.get(f"{reverse('main:search')}?q=scoped&scope=django&tab=users")

        self.assertEqual(response.context["active_search_tab"], "posts")
        self.assertEqual([tab["id"] for tab in response.context["search_tabs"]], ["posts"])
        self.assertContains(response, ">Posts<")
        self.assertNotContains(response, ">Users<")

    def test_subthread_create_post_modal_includes_code_toolbar(self):
        user = User.objects.create_user(username="gabe", password="testpass123")
        subthread = Subthread.objects.create(name="toolbar", description="Toolbar", created_by=user)

        self.client.force_login(user)
        response = self.client.get(reverse("main:subthread_detail", args=[subthread.name]))

        self.assertContains(response, 'data-code-insert="inline"')
        self.assertContains(response, 'data-code-insert="block"')
        self.assertContains(response, 'data-target="post-content"')

    def test_feed_posts_include_related_dummy_tags(self):
        user = User.objects.create_user(username="gina", password="testpass123")
        subthread = Subthread.objects.create(name="react", description="React", created_by=user)
        Post.objects.create(title="React rendering tips", content="Performance work", subthread=subthread, author=user)

        response = self.client.get(reverse("main:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "react")
        self.assertContains(response, "performance")
        self.assertContains(response, "optimization")

    def test_feed_post_author_links_to_user_profile(self):
        user = User.objects.create_user(username="harper", password="testpass123")
        subthread = Subthread.objects.create(name="author-links", description="Authors", created_by=user)
        Post.objects.create(title="Author post", content="Content", subthread=subthread, author=user)

        response = self.client.get(reverse("main:index"))

        self.assertContains(response, f'href="{reverse("main:user_profile", args=[user.username])}"')
        self.assertContains(response, f"u/{user.username}")

    def test_homepage_feed_orders_posts_by_upvotes_then_recency(self):
        user = User.objects.create_user(username="jules", password="testpass123")
        subthread = Subthread.objects.create(name="ranking", description="Ranking", created_by=user)
        Post.objects.create(title="Lower ranked post", content="Content", subthread=subthread, author=user, upvotes=1)
        Post.objects.create(title="Higher ranked post", content="Content", subthread=subthread, author=user, upvotes=10)

        response = self.client.get(reverse("main:index"))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertLess(content.index("Higher ranked post"), content.index("Lower ranked post"))

    def test_post_detail_vote_colors_are_neutral_until_user_votes(self):
        user = User.objects.create_user(username="hannah", password="testpass123")
        subthread = Subthread.objects.create(name="django", description="Django", created_by=user)
        post = Post.objects.create(title="A post", content="Content", subthread=subthread, author=user)

        self.client.force_login(user)
        neutral_response = self.client.get(reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id}))

        self.assertContains(neutral_response, "vote-neutral")

        Vote.objects.create(user=user, post=post, vote_type="up")
        voted_response = self.client.get(reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id}))

        self.assertContains(voted_response, "vote-up-active")

    def test_post_detail_downvote_uses_active_downvote_class(self):
        user = User.objects.create_user(username="ian", password="testpass123")
        subthread = Subthread.objects.create(name="webdev", description="Webdev", created_by=user)
        post = Post.objects.create(title="A post", content="Content", subthread=subthread, author=user)
        Vote.objects.create(user=user, post=post, vote_type="down")

        self.client.force_login(user)
        response = self.client.get(reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id}))

        self.assertContains(response, "vote-down-active")

    def test_post_detail_comment_threads_include_reply_toggle_and_collapse_control(self):
        user = User.objects.create_user(username="omar", password="testpass123")
        subthread = Subthread.objects.create(name="comment-ui", description="Comments", created_by=user)
        post = Post.objects.create(title="A post", content="Content", subthread=subthread, author=user)
        comment = Comment.objects.create(post=post, author=user, content="Top level comment")
        reply = Comment.objects.create(post=post, author=user, content="Nested reply", parent=comment)
        Comment.objects.create(post=post, author=user, content="Deep nested reply", parent=reply)

        self.client.force_login(user)
        response = self.client.get(reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id}))

        self.assertContains(response, "data-thread-toggle")
        self.assertContains(response, "data-reply-toggle")
        self.assertContains(response, f'id="reply-form-{comment.id}"')
        self.assertContains(response, f'id="reply-form-{reply.id}"')
        self.assertContains(response, f'placeholder="Reply to u/{user.username}"')
        self.assertContains(response, "2 replies")
        self.assertContains(response, "1 reply")

    def test_post_detail_author_and_comment_usernames_link_to_profiles(self):
        user = User.objects.create_user(username="orion", password="testpass123")
        subthread = Subthread.objects.create(name="profile-links", description="Profiles", created_by=user)
        post = Post.objects.create(title="A post", content="Content", subthread=subthread, author=user)
        Comment.objects.create(post=post, author=user, content="Comment body")

        response = self.client.get(reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id}))

        self.assertContains(response, f'href="{reverse("main:user_profile", args=[user.username])}"')
        self.assertContains(response, f"u/{user.username}")

    def test_post_detail_can_auto_open_comment_modal_from_query(self):
        user = User.objects.create_user(username="sage", password="testpass123")
        subthread = Subthread.objects.create(name="auto-comment", description="Comments", created_by=user)
        post = Post.objects.create(title="Auto comment", content="Content", subthread=subthread, author=user)

        self.client.force_login(user)
        response = self.client.get(
            f"{reverse('main:post_detail', kwargs={'name': subthread.name, 'post_id': post.id})}?open_comment=1"
        )

        self.assertContains(response, "const openCommentOnLoad = true;")

    def test_post_detail_only_shows_delete_action_to_post_author(self):
        author = User.objects.create_user(username="deleteauthor", password="testpass123")
        viewer = User.objects.create_user(username="deleteviewer", password="testpass123")
        subthread = Subthread.objects.create(name="delete-ui", description="Delete", created_by=author)
        post = Post.objects.create(title="Delete me", content="Content", subthread=subthread, author=author)

        self.client.force_login(author)
        owner_response = self.client.get(reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id}))
        self.assertContains(owner_response, 'id="open-delete-modal"')
        self.assertContains(owner_response, reverse("main:delete_post", kwargs={"name": subthread.name, "post_id": post.id}))

        self.client.force_login(viewer)
        viewer_response = self.client.get(reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id}))
        self.assertNotContains(viewer_response, 'id="open-delete-modal"')

    def test_post_author_can_delete_post_and_redirect_back(self):
        author = User.objects.create_user(username="deleteowner", password="testpass123")
        subthread = Subthread.objects.create(name="delete-post", description="Delete", created_by=author)
        post = Post.objects.create(title="Delete target", content="Content", subthread=subthread, author=author)
        Comment.objects.create(post=post, author=author, content="Comment that should go away")

        self.client.force_login(author)
        response = self.client.post(
            reverse("main:delete_post", kwargs={"name": subthread.name, "post_id": post.id}),
            {"next": reverse("main:subthread_detail", args=[subthread.name])},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("main:subthread_detail", args=[subthread.name]))
        self.assertFalse(Post.objects.filter(id=post.id).exists())
        self.assertEqual(Comment.objects.filter(post=post).count(), 0)

    def test_non_author_cannot_delete_someone_elses_post(self):
        author = User.objects.create_user(username="realowner", password="testpass123")
        viewer = User.objects.create_user(username="notowner", password="testpass123")
        subthread = Subthread.objects.create(name="forbidden-delete", description="Delete", created_by=author)
        post = Post.objects.create(title="Protected post", content="Content", subthread=subthread, author=author)

        self.client.force_login(viewer)
        response = self.client.post(reverse("main:delete_post", kwargs={"name": subthread.name, "post_id": post.id}))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Post.objects.filter(id=post.id).exists())

    def test_superuser_can_delete_someone_elses_post(self):
        author = User.objects.create_user(username="postowner", password="testpass123")
        superuser = User.objects.create_superuser(username="postsuper", email="postsuper@example.com", password="testpass123")
        subthread = Subthread.objects.create(name="super-delete", description="Delete", created_by=author)
        post = Post.objects.create(title="Super delete target", content="Content", subthread=subthread, author=author)

        self.client.force_login(superuser)
        response = self.client.post(
            reverse("main:delete_post", kwargs={"name": subthread.name, "post_id": post.id}),
            {"next": reverse("main:index")},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Post.objects.filter(id=post.id).exists())

    def test_superuser_can_boost_post_votes(self):
        author = User.objects.create_user(username="boostauthor", password="testpass123")
        superuser = User.objects.create_superuser(username="voteboss", email="voteboss@example.com", password="testpass123")
        subthread = Subthread.objects.create(name="boost-post", description="Boost", created_by=author)
        post = Post.objects.create(title="Boost me", content="Content", subthread=subthread, author=author)

        self.client.force_login(superuser)
        response = self.client.post(
            reverse("main:adjust_post_votes", args=[post.id]),
            {"vote_type": "up", "next": reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id})},
        )

        post.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(post.manual_upvotes, 1)
        self.assertEqual(post.upvotes, 1)

    def test_superuser_can_boost_and_delete_comments(self):
        author = User.objects.create_user(username="commentauthor", password="testpass123")
        superuser = User.objects.create_superuser(username="commentboss", email="commentboss@example.com", password="testpass123")
        subthread = Subthread.objects.create(name="boost-comment", description="Boost", created_by=author)
        post = Post.objects.create(title="Comment post", content="Content", subthread=subthread, author=author)
        comment = Comment.objects.create(post=post, author=author, content="Comment body")

        self.client.force_login(superuser)
        boost_response = self.client.post(
            reverse("main:adjust_comment_votes", args=[comment.id]),
            {"vote_type": "up", "next": reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id})},
        )

        comment.refresh_from_db()
        self.assertEqual(boost_response.status_code, 302)
        self.assertEqual(comment.manual_upvotes, 1)
        self.assertEqual(comment.upvotes, 1)

        delete_response = self.client.post(
            reverse("main:delete_comment", args=[comment.id]),
            {"next": reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id})},
        )

        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Comment.objects.filter(id=comment.id).exists())

    def test_superuser_can_delete_any_subthread(self):
        owner = User.objects.create_user(username="subowner", password="testpass123")
        superuser = User.objects.create_superuser(username="subboss", email="subboss@example.com", password="testpass123")
        subthread = Subthread.objects.create(name="super-subthread", description="Delete me", created_by=owner)

        self.client.force_login(superuser)
        response = self.client.post(reverse("main:delete_subthread", args=[subthread.name]), {"next": reverse("main:index")})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Subthread.objects.filter(id=subthread.id).exists())

    def test_superuser_ui_is_distinct(self):
        superuser = User.objects.create_superuser(username="distinctadmin", email="distinctadmin@example.com", password="testpass123")

        self.client.force_login(superuser)
        response = self.client.get(reverse("main:index"))

        self.assertContains(response, "superuser-mode")
        self.assertContains(response, "Superuser")

    def test_superuser_dashboard_renders_stats_and_recent_sections(self):
        owner = User.objects.create_user(username="dashboardowner", password="testpass123")
        superuser = User.objects.create_superuser(username="dashboardboss", email="dashboardboss@example.com", password="testpass123")
        subthread = Subthread.objects.create(name="dashboard-room", description="Room", created_by=owner)
        post = Post.objects.create(title="Dashboard post", content="Dashboard content", subthread=subthread, author=owner)
        Comment.objects.create(post=post, author=owner, content="Dashboard comment")

        self.client.force_login(superuser)
        response = self.client.get(reverse("main:superuser_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Moderation overview")
        self.assertContains(response, "Recent Posts")
        self.assertContains(response, "Recent Comments")
        self.assertContains(response, "Audit Log")
        self.assertContains(response, "Dashboard post")
        self.assertContains(response, "Dashboard comment")

    def test_superuser_actions_create_audit_log_entries(self):
        owner = User.objects.create_user(username="auditowner", password="testpass123")
        superuser = User.objects.create_superuser(username="auditboss", email="auditboss@example.com", password="testpass123")
        subthread = Subthread.objects.create(name="audit-room", description="Audit", created_by=owner)
        post = Post.objects.create(title="Audit post", content="Content", subthread=subthread, author=owner)
        comment = Comment.objects.create(post=post, author=owner, content="Audit comment")

        self.client.force_login(superuser)
        self.client.post(reverse("main:adjust_post_votes", args=[post.id]), {"vote_type": "up", "next": reverse("main:index")})
        self.client.post(reverse("main:adjust_comment_votes", args=[comment.id]), {"vote_type": "down", "next": reverse("main:index")})
        self.client.post(reverse("main:delete_comment", args=[comment.id]), {"next": reverse("main:index")})

        action_types = list(AdminAuditLog.objects.values_list("action_type", flat=True))
        self.assertIn(AdminAuditLog.ACTION_POST_VOTE_BOOST, action_types)
        self.assertIn(AdminAuditLog.ACTION_COMMENT_VOTE_BOOST, action_types)
        self.assertIn(AdminAuditLog.ACTION_COMMENT_DELETE, action_types)

    def test_post_detail_renders_copyable_code_for_posts_comments_and_replies(self):
        user = User.objects.create_user(username="rhea", password="testpass123")
        subthread = Subthread.objects.create(name="code-ui", description="Code", created_by=user)
        post = Post.objects.create(
            title="Code post",
            content="Use `print()` here.\n```\nprint('hello')\n```",
            subthread=subthread,
            author=user,
        )
        comment = Comment.objects.create(
            post=post,
            author=user,
            content="Comment with `len()`.\n```\nlen(items)\n```",
        )
        Comment.objects.create(
            post=post,
            author=user,
            parent=comment,
            content="Reply with `sum()`.\n```\nsum(values)\n```",
        )

        self.client.force_login(user)
        response = self.client.get(reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id}))

        self.assertContains(response, "inline-code-shell")
        self.assertContains(response, "code-block-shell")
        self.assertContains(response, "code-copy-button")
        self.assertContains(response, "print(&#x27;hello&#x27;)")
        self.assertContains(response, "len(items)")
        self.assertContains(response, "sum(values)")

    def test_vote_view_switches_and_removes_post_votes(self):
        user = User.objects.create_user(username="kai", password="testpass123")
        subthread = Subthread.objects.create(name="votes", description="Votes", created_by=user)
        post = Post.objects.create(title="A post", content="Content", subthread=subthread, author=user)

        self.client.force_login(user)

        response = self.client.post(reverse("main:vote_post", args=[post.id]), {"vote_type": "up"})
        post.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(post.upvotes, 1)
        self.assertEqual(post.downvotes, 0)

        response = self.client.post(reverse("main:vote_post", args=[post.id]), {"vote_type": "down"})
        post.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(post.upvotes, 0)
        self.assertEqual(post.downvotes, 1)
        self.assertEqual(Vote.objects.filter(user=user, post=post, comment__isnull=True).count(), 1)

        response = self.client.post(reverse("main:vote_post", args=[post.id]), {"vote_type": "down"})
        post.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(post.upvotes, 0)
        self.assertEqual(post.downvotes, 0)
        self.assertFalse(Vote.objects.filter(user=user, post=post, comment__isnull=True).exists())

    def test_feed_vote_redirects_back_to_next_url(self):
        user = User.objects.create_user(username="piper", password="testpass123")
        subthread = Subthread.objects.create(name="feed-votes", description="Feed", created_by=user)
        post = Post.objects.create(title="Feed post", content="Content", subthread=subthread, author=user)

        self.client.force_login(user)
        response = self.client.post(
            reverse("main:vote_post", args=[post.id]),
            {"vote_type": "up", "next": reverse("main:index")},
        )

        post.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("main:index"))
        self.assertEqual(post.upvotes, 1)

    def test_home_feed_shows_current_user_vote_state(self):
        user = User.objects.create_user(username="quinn", password="testpass123")
        subthread = Subthread.objects.create(name="feed-state", description="State", created_by=user)
        post = Post.objects.create(title="Feed state post", content="Content", subthread=subthread, author=user)
        Vote.objects.create(user=user, post=post, vote_type="up")

        self.client.force_login(user)
        response = self.client.get(reverse("main:index"))

        self.assertContains(response, reverse("main:vote_post", args=[post.id]))
        self.assertContains(response, 'name="next" value="/main/"')
        self.assertContains(response, "vote-up-active")

    def test_profile_tabs_render_clickable_links(self):
        user = User.objects.create_user(username="lena", password="testpass123")
        self.client.force_login(user)

        response = self.client.get(reverse("main:user_profile", args=[user.username]))

        self.assertContains(response, f'href="{reverse("main:user_profile", args=[user.username])}?tab=overview"')
        self.assertContains(response, f'href="{reverse("main:user_profile", args=[user.username])}?tab=posts"')
        self.assertContains(response, f'href="{reverse("main:user_profile", args=[user.username])}?tab=comments"')

    def test_own_profile_shows_hover_edit_photo_controls(self):
        user = User.objects.create_user(username="avatarowner", password="testpass123")
        self.client.force_login(user)

        response = self.client.get(reverse("main:user_profile", args=[user.username]))

        self.assertContains(response, 'id="profile-photo-form"')
        self.assertContains(response, 'id="profile-photo-input"')
        self.assertContains(response, 'id="profile-photo-trigger"')
        self.assertContains(response, 'class="profile-avatar-edit"')

    def test_profile_shows_default_bio_when_empty(self):
        user = User.objects.create_user(username="biodefault", password="testpass123")
        self.client.force_login(user)

        response = self.client.get(reverse("main:user_profile", args=[user.username]))

        self.assertContains(response, "No bio yet")
        self.assertContains(response, 'id="profile-bio-trigger"')

    def test_profile_bio_update_persists_and_renders(self):
        user = User.objects.create_user(username="biowriter", password="testpass123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("main:update_profile_bio"),
            {"bio": "Shipping Django features and tinkering with compilers."},
            follow=True,
        )

        preference = UserPreference.objects.get(user=user)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(preference.bio, "Shipping Django features and tinkering with compilers.")
        self.assertContains(response, "Bio updated.")
        self.assertContains(response, "Shipping Django features and tinkering with compilers.")

    def test_profile_bio_can_be_cleared_back_to_default_text(self):
        user = User.objects.create_user(username="bioclear", password="testpass123")
        UserPreference.objects.create(user=user, bio="Previously set bio")
        self.client.force_login(user)

        response = self.client.post(
            reverse("main:update_profile_bio"),
            {"bio": ""},
            follow=True,
        )

        preference = UserPreference.objects.get(user=user)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(preference.bio, "")
        self.assertContains(response, "Bio cleared.")
        self.assertContains(response, "No bio yet")

    def test_profile_photo_upload_updates_preference_and_renders_image(self):
        user = User.objects.create_user(username="photouser", password="testpass123")
        self.client.force_login(user)

        with self.settings(MEDIA_URL="/media/", STORAGES=self.TEST_STORAGES):
            response = self.client.post(
                reverse("main:update_profile_photo"),
                {
                    "profile_photo": SimpleUploadedFile(
                        "avatar.png",
                        b"fake image bytes",
                        content_type="image/png",
                    )
                },
                follow=True,
            )

            preference = UserPreference.objects.get(user=user)
            uploaded_url = preference.profile_photo.url

            self.assertEqual(response.status_code, 200)
            self.assertTrue(preference.profile_photo.name.startswith("profile_photos/"))
            self.assertContains(response, "Profile photo updated.")
            self.assertContains(response, f'src="{uploaded_url}"')

    def test_profile_photo_upload_rejects_non_image_files(self):
        user = User.objects.create_user(username="badphoto", password="testpass123")
        self.client.force_login(user)

        with self.settings(MEDIA_URL="/media/", STORAGES=self.TEST_STORAGES):
            response = self.client.post(
                reverse("main:update_profile_photo"),
                {
                    "profile_photo": SimpleUploadedFile(
                        "avatar.txt",
                        b"not an image",
                        content_type="text/plain",
                    )
                },
                follow=True,
            )

            preference = UserPreference.objects.get(user=user)

            self.assertEqual(response.status_code, 200)
            self.assertFalse(bool(preference.profile_photo))
            self.assertContains(response, "Use a JPG, PNG, GIF, or WebP image for your profile photo.")

    def test_profile_displays_computed_aura_and_achievement_counts(self):
        owner = User.objects.create_user(username="auradev", password="testpass123")
        responder = User.objects.create_user(username="aurafriend", password="testpass123")
        subthread = Subthread.objects.create(name="aura-zone", description="Aura", created_by=owner)
        post = Post.objects.create(title="Aura post", content="Content", subthread=subthread, author=owner, upvotes=5)
        owner_comment = Comment.objects.create(post=post, author=owner, content="Owner comment", upvotes=10)
        Comment.objects.create(post=post, author=responder, content="Top-level response")
        Comment.objects.create(post=post, author=responder, parent=owner_comment, content="Reply response")

        self.client.force_login(owner)
        response = self.client.get(reverse("main:user_profile", args=[owner.username]))

        reputation = response.context["profile_reputation"]

        self.assertEqual(reputation["total_aura"], 225)
        self.assertEqual(reputation["achievement_total"], 2)
        self.assertContains(response, "225 Aura")
        self.assertContains(response, "Achievements")
        self.assertContains(response, "Baby Steps")
        self.assertContains(response, "Adept")

    def test_user_hover_card_view_renders_aura_and_achievement_data(self):
        owner = User.objects.create_user(username="hoverowner", password="testpass123")
        subthread = Subthread.objects.create(name="hover-zone", description="Hover", created_by=owner)
        Post.objects.create(title="Advanced post", content="Content", subthread=subthread, author=owner, upvotes=15)

        response = self.client.get(reverse("main:user_hover_card", args=[owner.username]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aura")
        self.assertContains(response, "225")
        self.assertContains(response, "To The Stars")
        self.assertContains(response, "hoverowner")

    def test_post_detail_renders_achievement_badges_and_user_hover_trigger(self):
        owner = User.objects.create_user(username="badgeowner", password="testpass123")
        commenter = User.objects.create_user(username="badgecommenter", password="testpass123")
        subthread = Subthread.objects.create(name="badge-zone", description="Badges", created_by=owner)
        post = Post.objects.create(title="Badge post", content="Content", subthread=subthread, author=owner, upvotes=15)
        Comment.objects.create(post=post, author=commenter, content="Badge comment", upvotes=5)

        response = self.client.get(reverse("main:post_detail", kwargs={"name": subthread.name, "post_id": post.id}))

        self.assertContains(response, f'data-user-hover-url="{reverse("main:user_hover_card", args=[owner.username])}"')
        self.assertContains(response, 'data-achievement-level="advanced"')
        self.assertContains(response, 'data-achievement-level="beginner"')

    def test_profile_posts_tab_shows_only_posts(self):
        user = User.objects.create_user(username="mira", password="testpass123")
        subthread = Subthread.objects.create(name="profile-posts", description="Posts", created_by=user)
        post = Post.objects.create(title="My profile post", content="Hello world", subthread=subthread, author=user)
        Comment.objects.create(post=post, author=user, content="My profile comment body")

        self.client.force_login(user)
        response = self.client.get(f"{reverse('main:user_profile', args=[user.username])}?tab=posts")

        self.assertEqual(response.context["active_tab"], "posts")
        self.assertContains(response, "My profile post")
        self.assertContains(response, f'href="{reverse("main:user_profile", args=[user.username])}?tab=posts"')

    def test_profile_comments_tab_shows_only_comments(self):
        user = User.objects.create_user(username="nora", password="testpass123")
        subthread = Subthread.objects.create(name="profile-comments", description="Comments", created_by=user)
        post = Post.objects.create(title="Post title", content="Post body", subthread=subthread, author=user)
        Comment.objects.create(post=post, author=user, content="This is my comment")

        self.client.force_login(user)
        response = self.client.get(f"{reverse('main:user_profile', args=[user.username])}?tab=comments")

        self.assertEqual(response.context["active_tab"], "comments")
        self.assertContains(response, "This is my comment")
        self.assertNotContains(response, "No comments yet.")
