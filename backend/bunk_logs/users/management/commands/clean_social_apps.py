import logging

from allauth.socialaccount.models import SocialApp
from django.core.management.base import BaseCommand
from django.db.models import Count

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Cleans up duplicate SocialApp entries in the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without actually making changes",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)

        # Find duplicate providers (same provider, different records)
        provider_counts = (
            SocialApp.objects.values("provider")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
        )

        if not provider_counts:
            self.stdout.write(self.style.SUCCESS("No duplicate providers found!"))
            return

        self.stdout.write(f"Found {len(provider_counts)} providers with duplicates:")
        for provider_count in provider_counts:
            provider = provider_count["provider"]
            count = provider_count["count"]
            self.stdout.write(f"- {provider}: {count} entries")

            # Get all the apps for this provider
            apps = SocialApp.objects.filter(provider=provider).order_by("id")
            
            # Display app details
            for i, app in enumerate(apps):
                self.stdout.write(
                    f"  {i+1}. ID={app.id}, Name={app.name}, Client ID={app.client_id[:10]}..., "
                    f"Created: {getattr(app, 'created_at', 'N/A')}"
                )

            # Keep the first one, delete the rest
            if not dry_run:
                # Get the first app (we'll keep this one)
                keep_app = apps.first()
                self.stdout.write(
                    self.style.SUCCESS(f"  Keeping: {keep_app.id} - {keep_app.name}")
                )
                
                # Delete the rest
                for app in apps[1:]:
                    self.stdout.write(
                        self.style.WARNING(f"  Deleting: {app.id} - {app.name}")
                    )
                    app.delete()
                
                self.stdout.write(
                    self.style.SUCCESS(f"Cleaned up duplicate entries for {provider}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [DRY RUN] Would keep {apps[0].id} and delete {len(apps)-1} duplicates"
                    )
                )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "This was a dry run. No changes were made. "
                    "Run without --dry-run to apply changes."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("Successfully cleaned up duplicate social apps")
            )