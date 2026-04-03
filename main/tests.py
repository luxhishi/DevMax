from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse

from .models import Comment, Post, Subthread, UserPreference, Vote


class RoutingTests(TestCase):
    def test_root_redirects_to_main_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("main:index"))

    def test_main_named_routes_reverse_to_main_prefix(self):
        self.assertEqual(reverse("main:index"), "/main/")
        self.assertEqual(reverse("main:search"), "/main/search/")
        self.assertEqual(reverse("main:update_display_mode"), "/main/display-mode/")
        self.assertEqual(reverse("main:login"), "/main/login/")
        self.assertEqual(reverse("main:profile"), "/main/profile/")
        self.assertEqual(reverse("main:subthread_detail", args=["python"]), "/main/d/python/")
        self.assertEqual(reverse("main:create_post", args=["python"]), "/main/d/python/create-post/")
        self.assertEqual(reverse("main:post_detail", kwargs={"name": "python", "post_id": 42}), "/main/d/python/42/")

    def test_main_index_route_resolves(self):
        self.assertEqual(resolve("/main/").view_name, "main:index")

    def test_profile_requires_login(self):
        response = self.client.get(reverse("main:profile"))
        self.assertEqual(response.status_code, 302)

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

    def test_post_detail_can_auto_open_comment_modal_from_query(self):
        user = User.objects.create_user(username="sage", password="testpass123")
        subthread = Subthread.objects.create(name="auto-comment", description="Comments", created_by=user)
        post = Post.objects.create(title="Auto comment", content="Content", subthread=subthread, author=user)

        self.client.force_login(user)
        response = self.client.get(
            f"{reverse('main:post_detail', kwargs={'name': subthread.name, 'post_id': post.id})}?open_comment=1"
        )

        self.assertContains(response, "const openCommentOnLoad = true;")

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

        response = self.client.get(reverse("main:profile"))

        self.assertContains(response, f'href="{reverse("main:profile")}?tab=overview"')
        self.assertContains(response, f'href="{reverse("main:profile")}?tab=posts"')
        self.assertContains(response, f'href="{reverse("main:profile")}?tab=comments"')

    def test_profile_posts_tab_shows_only_posts(self):
        user = User.objects.create_user(username="mira", password="testpass123")
        subthread = Subthread.objects.create(name="profile-posts", description="Posts", created_by=user)
        post = Post.objects.create(title="My profile post", content="Hello world", subthread=subthread, author=user)
        Comment.objects.create(post=post, author=user, content="My profile comment body")

        self.client.force_login(user)
        response = self.client.get(f"{reverse('main:profile')}?tab=posts")

        self.assertEqual(response.context["active_tab"], "posts")
        self.assertContains(response, "My profile post")
        self.assertContains(response, 'href="/main/profile/?tab=posts"')

    def test_profile_comments_tab_shows_only_comments(self):
        user = User.objects.create_user(username="nora", password="testpass123")
        subthread = Subthread.objects.create(name="profile-comments", description="Comments", created_by=user)
        post = Post.objects.create(title="Post title", content="Post body", subthread=subthread, author=user)
        Comment.objects.create(post=post, author=user, content="This is my comment")

        self.client.force_login(user)
        response = self.client.get(f"{reverse('main:profile')}?tab=comments")

        self.assertEqual(response.context["active_tab"], "comments")
        self.assertContains(response, "This is my comment")
        self.assertNotContains(response, "No comments yet.")
