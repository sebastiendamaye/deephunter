"""
Management command: create_api_token

Generates a django-rest-knox API token for an existing user so they can call
the DeepHunter REST API (mounted at /api/) without a local username/password.

Because the app authenticates humans through an external provider (PingID /
EntraID), user accounts exist in the DB but have no usable password. Knox
tokens are minted for a user that already exists and do NOT require a
password, which makes them the right credential for programmatic API access
under a "no local passwords" policy.

The plaintext token is shown ONCE, here, at creation time. Knox only stores a
hash of it, so it can never be re-displayed. If it is lost, generate a new one
and (optionally) revoke the old one.

Examples:
    # 90-day token (default) for a PingID user
    python manage.py create_api_token jdoe

    # custom lifetime
    python manage.py create_api_token jdoe --days 30

    # non-expiring token (rotate/revoke manually)
    python manage.py create_api_token svc-ai-assistant --no-expiry

    # also grant the model permissions the API requires
    python manage.py create_api_token jdoe --grant-perms
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from knox.models import AuthToken

# Permissions the REST API enforces via DjangoModelPermissions.
# See qm/api.py / docs/api.rst.
API_PERMISSIONS = ('qm.view_analytic', 'qm.add_analytic')


class Command(BaseCommand):
    help = "Create a Knox API token for an existing user (no password required)."

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            help="Username of an existing account to mint the token for.",
        )
        expiry = parser.add_mutually_exclusive_group()
        expiry.add_argument(
            '--days',
            type=int,
            default=90,
            help="Token lifetime in days (default: 90). Overrides the global "
                 "REST_KNOX TOKEN_TTL for this token only.",
        )
        expiry.add_argument(
            '--no-expiry',
            action='store_true',
            help="Mint a non-expiring token (rotate/revoke manually).",
        )
        parser.add_argument(
            '--grant-perms',
            action='store_true',
            help="Also grant the model permissions the API requires "
                 f"({', '.join(API_PERMISSIONS)}).",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(
                f"No user with username '{username}'. The account must already "
                f"exist (it is created on first login via the auth provider)."
            )

        if not user.is_active:
            raise CommandError(
                f"User '{username}' is inactive; refusing to mint a token."
            )

        if options['grant_perms']:
            self._grant_api_permissions(user)

        expiry = None if options['no_expiry'] else timedelta(days=options['days'])
        _instance, token = AuthToken.objects.create(user, expiry=expiry)

        if expiry is None:
            lifetime = "non-expiring"
        else:
            lifetime = f"valid for {options['days']} day(s)"

        self._report(user, token, lifetime)

    def _grant_api_permissions(self, user):
        for perm in API_PERMISSIONS:
            app_label, codename = perm.split('.')
            try:
                permission = Permission.objects.get(
                    content_type__app_label=app_label, codename=codename
                )
            except Permission.DoesNotExist:
                raise CommandError(f"Permission '{perm}' not found.")
            user.user_permissions.add(permission)
        self.stdout.write(self.style.SUCCESS(
            f"Granted {', '.join(API_PERMISSIONS)} to '{user.username}'."
        ))

    def _report(self, user, token, lifetime):
        self.stdout.write(self.style.SUCCESS(
            f"\nAPI token for '{user.username}' ({lifetime}):"
        ))
        self.stdout.write(f"\n    {token}\n")
        self.stdout.write(self.style.WARNING(
            "Copy it now - it is shown only once and cannot be retrieved again.\n"
        ))
        self.stdout.write("Use it as an HTTP header:")
        self.stdout.write(f'    Authorization: Token {token}\n')
        self.stdout.write("Example:")
        self.stdout.write(
            '    curl https://deephunterdev.se.com/api/analytics/ \\\n'
            f'         -H "Authorization: Token {token}"\n'
        )
