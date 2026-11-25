import getpass
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

class Command(BaseCommand):
    help = "Create the first SXC Clubs administrator interactively."
    def handle(self, *args, **options):
        User=get_user_model()
        if User.objects.filter(is_superuser=True).exists(): raise CommandError("A superuser already exists.")
        username=input("Admin username: ").strip()
        email=input("Admin email: ").strip()
        password=getpass.getpass("Password: ")
        try: validate_password(password)
        except ValidationError as e: raise CommandError(" ".join(e.messages))
        user=User.objects.create_superuser(username=username,email=email,password=password)
        self.stdout.write(self.style.SUCCESS(f"Created administrator {user.username}."))
