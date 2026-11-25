import hashlib
import secrets
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator

def validate_upload_size(file):
    if file.size > 5 * 1024 * 1024: raise ValidationError("Files must be 5 MB or smaller.")

class Permission(models.Model):
    key = models.CharField(max_length=64, unique=True)
    group = models.CharField(max_length=32, db_index=True)
    label = models.CharField(max_length=80)
    class Meta: ordering = ["group", "key"]
    def __str__(self): return self.label

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    student_id = models.CharField(max_length=32, blank=True, unique=True, null=True)
    phone = models.CharField(max_length=32, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True, validators=[validate_upload_size])
    created_at = models.DateTimeField(auto_now_add=True)

class Club(models.Model):
    STATUS = [("active", "Active"), ("archived", "Archived")]
    name = models.CharField(max_length=120, unique=True)
    abbreviation = models.CharField(max_length=16, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=64, blank=True)
    logo = models.ImageField(upload_to="clubs/logos/", blank=True, null=True, validators=[validate_upload_size])
    banner = models.ImageField(upload_to="clubs/banners/", blank=True, null=True, validators=[validate_upload_size])
    contact_email = models.EmailField(blank=True)
    contact_url = models.URLField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="active", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: ordering = ["name"]
    def __str__(self): return self.name

class ClubMembership(models.Model):
    STATUS = [("active", "Active"), ("pending", "Pending"), ("removed", "Removed")]
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="club_memberships")
    role_name = models.CharField(max_length=64, default="Member")
    permissions = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="active", db_index=True)
    joined_at = models.DateTimeField(default=timezone.now)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["club", "user"], name="unique_club_membership")]
        indexes = [models.Index(fields=["club", "status"]), models.Index(fields=["user", "status"])]

class JoinCode(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="join_codes")
    role_name = models.CharField(max_length=64)
    permissions = models.JSONField(default=list, blank=True)
    code_hash = models.CharField(max_length=64, unique=True, db_index=True)
    code_hint = models.CharField(max_length=8)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    uses = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    @staticmethod
    def digest(code): return hashlib.sha256(code.strip().upper().encode()).hexdigest()
    @staticmethod
    def generate(): return "SXC-" + secrets.token_urlsafe(9).upper()
    @property
    def is_valid(self): return not self.revoked_at and (not self.expires_at or self.expires_at > timezone.now()) and (self.max_uses is None or self.uses < self.max_uses)

class Event(models.Model):
    STATUS = [("draft", "Draft"), ("published", "Published"), ("completed", "Completed"), ("cancelled", "Cancelled")]
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    banner = models.ImageField(upload_to="events/", blank=True, null=True, validators=[validate_upload_size])
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=160, blank=True)
    category = models.CharField(max_length=64, blank=True)
    registration_url = models.URLField(blank=True)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="draft", db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: ordering = ["starts_at"]

class Announcement(models.Model):
    STATUS = [("draft", "Draft"), ("published", "Published"), ("archived", "Archived")]
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=180)
    content = models.TextField()
    attachment = models.FileField(upload_to="announcements/", blank=True, null=True, validators=[validate_upload_size, FileExtensionValidator(["pdf", "png", "jpg", "jpeg", "doc", "docx"])])
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=16, choices=STATUS, default="draft", db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: ordering = ["-published_at", "-created_at"]

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    club = models.ForeignKey(Club, on_delete=models.CASCADE, null=True, blank=True)
    kind = models.CharField(max_length=40)
    message = models.CharField(max_length=240)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta: ordering = ["-created_at"]

class ActivityLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=64, db_index=True)
    summary = models.CharField(max_length=240)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta: ordering = ["-created_at"]

def log_activity(actor, action, summary, club=None, metadata=None):
    ActivityLog.objects.create(actor=actor if getattr(actor, "is_authenticated", False) else None, club=club, action=action, summary=summary, metadata=metadata or {})
