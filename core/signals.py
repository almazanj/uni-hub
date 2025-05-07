from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Post, Notification
from django.contrib.auth.models import User

@receiver(post_save, sender=Post)
def notify_community_members_on_post(sender, instance, created, **kwargs):
    if created:
        print(f"📢 New post created in {instance.community.name}")  # debug log
        community = instance.community
        post_author = instance.author  # assuming your Post model has `author`

        # Notify all members of the community except the author
        for member in community.members.exclude(id=post_author.id):
            Notification.objects.create(
                user=member,
                title=f"New post in {community.name}",
                message=f"{post_author.first_name} posted: '{instance.title}'",
                link=f"/communities/{community.slug}/posts/{instance.pk}/",  # adjust this path to your URL pattern
                is_read=False
            )

