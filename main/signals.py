from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Comment, Notification, Post, Subthread, SubthreadMembership


def _sync_members_total(subthread_id):
    member_count = SubthreadMembership.objects.filter(subthread_id=subthread_id).count()
    Subthread.objects.filter(id=subthread_id).update(members=member_count)


def _create_notification(user_id, actor_id, notification_type, subthread_id=None, post_id=None, comment_id=None):
    if not user_id or user_id == actor_id:
        return

    Notification.objects.create(
        user_id=user_id,
        actor_id=actor_id,
        notification_type=notification_type,
        subthread_id=subthread_id,
        post_id=post_id,
        comment_id=comment_id,
    )


@receiver(post_save, sender=Subthread)
def ensure_creator_membership(sender, instance, created, **kwargs):
    if not created:
        return

    SubthreadMembership.objects.get_or_create(user=instance.created_by, subthread=instance)


@receiver(post_save, sender=SubthreadMembership)
def sync_members_after_join(sender, instance, **kwargs):
    _sync_members_total(instance.subthread_id)


@receiver(post_delete, sender=SubthreadMembership)
def sync_members_after_leave(sender, instance, **kwargs):
    _sync_members_total(instance.subthread_id)


@receiver(post_save, sender=Post)
def create_post_notifications(sender, instance, created, **kwargs):
    if not created:
        return

    recipient_ids = set(
        SubthreadMembership.objects.filter(subthread=instance.subthread)
        .exclude(user=instance.author)
        .values_list("user_id", flat=True)
    )
    if instance.subthread.created_by_id != instance.author_id:
        recipient_ids.add(instance.subthread.created_by_id)

    for user_id in recipient_ids:
        _create_notification(
            user_id=user_id,
            actor_id=instance.author_id,
            notification_type=Notification.TYPE_SUBTHREAD_POST,
            subthread_id=instance.subthread_id,
            post_id=instance.id,
        )


@receiver(post_save, sender=Comment)
def create_comment_notifications(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.parent_id:
        _create_notification(
            user_id=instance.parent.author_id,
            actor_id=instance.author_id,
            notification_type=Notification.TYPE_COMMENT_REPLY,
            subthread_id=instance.post.subthread_id,
            post_id=instance.post_id,
            comment_id=instance.id,
        )

    if instance.post.author_id != instance.author_id:
        _create_notification(
            user_id=instance.post.author_id,
            actor_id=instance.author_id,
            notification_type=Notification.TYPE_POST_COMMENT,
            subthread_id=instance.post.subthread_id,
            post_id=instance.post_id,
            comment_id=instance.id,
        )
