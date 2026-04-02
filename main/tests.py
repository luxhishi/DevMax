from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse

from .models import Post, Subthread, UserPreference, Vote


class RoutingTests(TestCase):
    def test_root_redirects_to_main_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("main:index"))

    def test_main_named_routes_reverse_to_main_prefix(self):
        self.assertEqual(reverse("main:index"), "/main/")
        self.assertEqual(reverse("main:update_display_mode"), "/main/display-mode/")
        self.assertEqual(reverse("main:login"), "/main/login/")
        self.assertEqual(reverse("main:profile"), "/main/profile/")
        self.assertEqual(reverse("main:subthread_detail", args=["python"]), "/main/d/python/")
        self.assertEqual(reverse("main:create_post", args=["python"]), "/main/d/python/create-post/")

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
        self.assertContains(response, reverse("main:post_detail", args=[welcome_post.id]))

    def test_post_detail_back_link_uses_subthread_context(self):
        user = User.objects.create_user(username="erin", password="testpass123")
        subthread = Subthread.objects.create(name="webdev", description="Webdev", created_by=user)
        post = Post.objects.create(title="Best Tailwind Plugins?", content="Content", subthread=subthread, author=user)

        response = self.client.get(f"{reverse('main:post_detail', args=[post.id])}?from_subthread={subthread.name}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{reverse("main:subthread_detail", args=[subthread.name])}"')

    def test_subthread_posts_link_back_to_same_subthread(self):
        user = User.objects.create_user(username="frank", password="testpass123")
        subthread = Subthread.objects.create(name="frontend", description="Frontend", created_by=user)
        post = Post.objects.create(title="A post", content="Content", subthread=subthread, author=user)

        response = self.client.get(reverse("main:subthread_detail", args=[subthread.name]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"{reverse('main:post_detail', args=[post.id])}?from_subthread={subthread.name}")

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
        neutral_response = self.client.get(reverse("main:post_detail", args=[post.id]))

        self.assertContains(neutral_response, "vote-neutral")

        Vote.objects.create(user=user, post=post, vote_type="up")
        voted_response = self.client.get(reverse("main:post_detail", args=[post.id]))

        self.assertContains(voted_response, "vote-up-active")

    def test_post_detail_downvote_uses_active_downvote_class(self):
        user = User.objects.create_user(username="ian", password="testpass123")
        subthread = Subthread.objects.create(name="webdev", description="Webdev", created_by=user)
        post = Post.objects.create(title="A post", content="Content", subthread=subthread, author=user)
        Vote.objects.create(user=user, post=post, vote_type="down")

        self.client.force_login(user)
        response = self.client.get(reverse("main:post_detail", args=[post.id]))

        self.assertContains(response, "vote-down-active")

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
