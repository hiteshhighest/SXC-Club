from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Club, ClubMembership, JoinCode, Event, Announcement, Notification, ActivityLog
from .permissions import ALL_PERMISSIONS

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "name"]
    def get_name(self, obj): return obj.get_full_name() or obj.username

class ClubSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Club
        fields = ["id", "name", "abbreviation", "description", "category", "logo", "banner", "contact_email", "contact_url", "status", "member_count", "created_at"]

class MembershipSerializer(serializers.ModelSerializer):
    student = UserSerializer(source="user", read_only=True)
    class Meta:
        model = ClubMembership
        fields = ["id", "student", "role_name", "permissions", "status", "joined_at"]
        read_only_fields = ["id", "student", "permissions", "joined_at"]

class JoinCodeCreateSerializer(serializers.Serializer):
    club = serializers.PrimaryKeyRelatedField(queryset=Club.objects.filter(status="active"))
    role_name = serializers.CharField(max_length=64)
    permissions = serializers.ListField(child=serializers.ChoiceField(choices=sorted(ALL_PERMISSIONS)), required=False, default=list)
    max_uses = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)

class AdminClubAccountSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    club = serializers.PrimaryKeyRelatedField(queryset=Club.objects.filter(status="active"))
    role_name = serializers.CharField(max_length=64, default="Member")
    permissions = serializers.ListField(child=serializers.ChoiceField(choices=sorted(ALL_PERMISSIONS)), required=False, default=list)

class JoinCodeSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    class Meta:
        model = JoinCode
        fields = ["id", "club", "club_name", "role_name", "permissions", "code_hint", "max_uses", "uses", "expires_at", "revoked_at", "created_at"]
        read_only_fields = fields

class EventSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    class Meta:
        model = Event
        fields = ["id", "club", "club_name", "title", "description", "banner", "starts_at", "ends_at", "venue", "category", "registration_url", "registration_deadline", "status", "created_by", "created_at", "updated_at"]
        read_only_fields = ["club", "created_by", "created_at", "updated_at"]
    def validate(self, attrs):
        start = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        end = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if end and start and end < start: raise serializers.ValidationError({"ends_at": "End time must be after start time."})
        return attrs

class AnnouncementSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    author_name = serializers.SerializerMethodField()
    class Meta:
        model = Announcement
        fields = ["id", "club", "club_name", "title", "content", "attachment", "author", "author_name", "status", "published_at", "created_at", "updated_at"]
        read_only_fields = ["club", "author", "published_at", "created_at", "updated_at"]
    def get_author_name(self, obj): return obj.author.get_full_name() if obj.author else "Former member"

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "club", "kind", "message", "read_at", "created_at"]

class ActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    club_name = serializers.CharField(source="club.name", read_only=True)
    class Meta:
        model = ActivityLog
        fields = ["id", "actor_name", "club", "club_name", "action", "summary", "metadata", "created_at"]
    def get_actor_name(self, obj): return obj.actor.get_full_name() if obj.actor else "System"
