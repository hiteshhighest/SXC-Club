from datetime import timedelta
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.csrf import csrf_protect
from rest_framework import viewsets, status, generics
from rest_framework.decorators import api_view, permission_classes, action, throttle_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.throttling import AnonRateThrottle
from .models import Club, ClubMembership, JoinCode, Event, Announcement, Notification, ActivityLog, log_activity
from .permissions import has_club_permission, ALL_PERMISSIONS, PERMISSION_GROUPS
from .serializers import (UserSerializer, ClubSerializer, MembershipSerializer, JoinCodeCreateSerializer,
    JoinCodeSerializer, EventSerializer, AnnouncementSerializer, NotificationSerializer, ActivitySerializer, AdminClubAccountSerializer)

User = get_user_model()

class LoginThrottle(AnonRateThrottle):
    scope = "login"

@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def csrf_token(request): return Response({"detail": "CSRF cookie set"})

def _login(request, admin_login=False):
    user = authenticate(request, username=request.data.get("username", ""), password=request.data.get("password", ""))
    if not user: return Response({"detail": "Invalid username or password."}, status=status.HTTP_400_BAD_REQUEST)
    if not user.is_active: return Response({"detail": "This account is inactive."}, status=status.HTTP_403_FORBIDDEN)
    is_admin = user.is_staff or user.is_superuser
    if is_admin != admin_login:
        message = "Use the administrator sign-in for this account." if is_admin else "This is a student account. Use student sign-in."
        return Response({"detail": message}, status=status.HTTP_403_FORBIDDEN)
    login(request, user)
    return _me_payload(user)

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
@csrf_protect
def login_view(request): return _login(request, admin_login=False)

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
@csrf_protect
def admin_login_view(request): return _login(request, admin_login=True)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request): logout(request); return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request): return _me_payload(request.user)

def _me_payload(user):
    data = UserSerializer(user).data
    data["is_admin"] = user.is_staff or user.is_superuser
    data["memberships"] = list(user.club_memberships.filter(status="active").select_related("club").values("club_id", "club__name", "club__abbreviation", "club__category", "role_name", "permissions"))
    return Response(data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_me_view(request):
    if request.user.is_staff or request.user.is_superuser: raise PermissionDenied("Use the administrator workspace.")
    return _me_payload(request.user)

@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_me_view(request): return _me_payload(request.user)

class PasswordResetRequest(generics.GenericAPIView):
    permission_classes = [AllowAny]
    def post(self, request):
        # Account reset links are sent only by Django's configured email backend; avoid revealing whether an account exists.
        from django.contrib.auth.forms import PasswordResetForm
        form = PasswordResetForm({"email": request.data.get("email", "")})
        if form.is_valid(): form.save(request=request, use_https=request.is_secure(), email_template_name="registration/password_reset_email.txt", subject_template_name="registration/password_reset_subject.txt", extra_email_context={"frontend_url": settings.FRONTEND_URL})
        return Response({"detail": "If the account exists, reset instructions will be sent."})

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    uid, token, password = request.data.get("uid", ""), request.data.get("token", ""), request.data.get("password", "")
    try: user = User.objects.get(pk=urlsafe_base64_decode(uid).decode())
    except Exception: user = None
    if not user or not default_token_generator.check_token(user, token): raise ValidationError({"detail": "This password reset link is invalid or expired."})
    try: validate_password(password, user)
    except DjangoValidationError as e: raise ValidationError({"password": list(e.messages)})
    user.set_password(password); user.save(update_fields=["password"])
    return Response({"detail": "Password updated. You can now log in."})

class ClubViewSet(viewsets.ModelViewSet):
    serializer_class = ClubSerializer
    def get_queryset(self):
        qs = Club.objects.annotate(member_count=Count("memberships", filter=Q(memberships__status="active")))
        if self.request.user.is_staff or self.request.user.is_superuser: return qs
        return qs.filter(status="active")
    def get_permissions(self): return [IsAuthenticated()] if self.action in ["create", "update", "partial_update", "destroy"] else [AllowAny()]
    def perform_create(self, serializer):
        if not (self.request.user.is_staff or self.request.user.is_superuser): raise PermissionDenied()
        club = serializer.save(); log_activity(self.request.user, "club.created", f"Created {club.name}", club)
    def perform_update(self, serializer):
        club=self.get_object()
        if not (self.request.user.is_staff or self.request.user.is_superuser or has_club_permission(self.request.user, club, "club.edit")): raise PermissionDenied()
        if "status" in serializer.validated_data and serializer.validated_data["status"] != club.status and not (self.request.user.is_staff or self.request.user.is_superuser): raise PermissionDenied("Only administrators can archive or reactivate a club.")
        obj=serializer.save(); log_activity(self.request.user,"club.updated",f"Updated {obj.name}",obj)
    def perform_destroy(self, instance):
        if not (self.request.user.is_staff or self.request.user.is_superuser): raise PermissionDenied()
        instance.status = "archived"; instance.save(update_fields=["status", "updated_at"])
        log_activity(self.request.user, "club.archived", f"Archived {instance.name}", instance)
    @action(detail=True, methods=["get"])
    def dashboard(self, request, pk=None):
        club = self.get_object(); active = club.memberships.filter(status="active")
        return Response({"club": self.get_serializer(club).data, "my_membership": MembershipSerializer(active.filter(user=request.user).first()).data if active.filter(user=request.user).exists() else None,
            "executives": MembershipSerializer(active.exclude(role_name__iexact="Member").select_related("user"), many=True).data,
            "members_count": active.count(), "upcoming_events": EventSerializer(club.events.filter(status="published", starts_at__gte=timezone.now())[:5], many=True).data,
            "announcements": AnnouncementSerializer(club.announcements.filter(status="published").order_by("-published_at")[:5], many=True).data})

class MembershipViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MembershipSerializer
    def get_queryset(self):
        club = Club.objects.filter(pk=self.kwargs.get("club_pk")).first()
        if not club: return ClubMembership.objects.none()
        if not has_club_permission(self.request.user, club, "members.view") and not self.request.user.is_staff: raise PermissionDenied()
        qs = club.memberships.filter(status="active").select_related("user")
        query = self.request.query_params.get("search")
        if query: qs = qs.filter(Q(user__first_name__icontains=query)|Q(user__last_name__icontains=query)|Q(user__email__icontains=query)|Q(role_name__icontains=query))
        role = self.request.query_params.get("role")
        if role: qs = qs.filter(role_name__iexact=role)
        return qs
    @action(detail=True, methods=["patch"])
    def role(self, request, club_pk=None, pk=None):
        membership = self.get_object()
        if not has_club_permission(request.user, membership.club, "members.change_role"): raise PermissionDenied()
        if not request.user.is_staff and not has_club_permission(request.user, membership.club, "executives.permissions") and request.data.get("role_name", "Member").lower() != "member": raise PermissionDenied("Only club administrators can assign executive roles.")
        membership.role_name = request.data.get("role_name", membership.role_name)[:64]
        # Role labels never grant permissions. Permission editing is a separate, constrained admin action.
        membership.save(update_fields=["role_name"])
        log_activity(request.user, "membership.role_changed", "Changed member role", membership.club, {"membership_id": membership.id})
        return Response(self.get_serializer(membership).data)
    @action(detail=True, methods=["delete"])
    def remove(self, request, club_pk=None, pk=None):
        membership = self.get_object()
        if not has_club_permission(request.user, membership.club, "members.remove"): raise PermissionDenied()
        if membership.user_id == request.user.id and not request.user.is_staff: raise PermissionDenied("You cannot remove your own membership.")
        membership.status = "removed"; membership.save(update_fields=["status"])
        log_activity(request.user, "membership.removed", "Removed a club member", membership.club, {"membership_id": membership.id})
        return Response(status=204)
    @action(detail=True, methods=["patch"])
    def permissions(self, request, club_pk=None, pk=None):
        membership=ClubMembership.objects.filter(pk=pk,club_id=club_pk,status="active").select_related("club","user").first()
        if not membership: return Response({"detail":"Not found."},status=404)
        if not has_club_permission(request.user,membership.club,"executives.permissions"): raise PermissionDenied()
        requested=request.data.get("permissions",[])
        if not isinstance(requested,list) or not set(requested).issubset(ALL_PERMISSIONS): raise ValidationError({"permissions":"Choose valid club permissions."})
        if not (request.user.is_staff or request.user.is_superuser):
            actor=membership.club.memberships.filter(user=request.user,status="active").first()
            if not actor or not set(requested).issubset(set(actor.permissions)): raise PermissionDenied("You cannot grant permissions you do not have.")
        membership.permissions=sorted(set(requested)); membership.save(update_fields=["permissions"])
        log_activity(request.user,"membership.permissions_changed","Updated club permissions",membership.club,{"membership_id":membership.id})
        return Response(self.get_serializer(membership).data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_join_code(request):
    serializer = JoinCodeCreateSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    data = serializer.validated_data; club = data["club"]
    if not (request.user.is_staff or has_club_permission(request.user, club, "join_codes.generate")): raise PermissionDenied()
    requested = set(data["permissions"])
    if not (request.user.is_staff or request.user.is_superuser):
        actor = club.memberships.filter(user=request.user, status="active").first()
        if not actor or not requested.issubset(set(actor.permissions)): raise PermissionDenied("You cannot grant permissions you do not have.")
    raw = JoinCode.generate(); code = JoinCode.objects.create(club=club, role_name=data["role_name"], permissions=list(requested), code_hash=JoinCode.digest(raw), code_hint=raw[-4:], max_uses=data.get("max_uses"), expires_at=data.get("expires_at"), created_by=request.user)
    log_activity(request.user, "join_code.created", f"Created a join code for {club.name}", club, {"join_code_id": code.id, "role_name": code.role_name})
    return Response({**JoinCodeSerializer(code).data, "code": raw}, status=201)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_join_codes(request):
    qs=JoinCode.objects.select_related("club").order_by("-created_at")
    if not request.user.is_staff and not request.user.is_superuser:
        ids=[m.club_id for m in request.user.club_memberships.filter(status="active") if has_club_permission(request.user,m.club,"join_codes.generate") or has_club_permission(request.user,m.club,"join_codes.revoke")]
        qs=qs.filter(club_id__in=ids)
    return Response(JoinCodeSerializer(qs, many=True).data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def revoke_join_code(request, pk):
    code = JoinCode.objects.filter(pk=pk).first()
    if not code: return Response({"detail": "Not found."}, status=404)
    if not (request.user.is_staff or has_club_permission(request.user, code.club, "join_codes.revoke")): raise PermissionDenied()
    code.revoked_at = timezone.now(); code.save(update_fields=["revoked_at"])
    log_activity(request.user, "join_code.revoked", f"Revoked a join code for {code.club.name}", code.club, {"join_code_id": code.id})
    return Response(JoinCodeSerializer(code).data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def redeem_join_code(request):
    raw = str(request.data.get("code", "")).strip()
    if not raw or len(raw) > 80: raise ValidationError({"code": "Enter a valid join code."})
    with transaction.atomic():
        code = JoinCode.objects.select_for_update().select_related("club").filter(code_hash=JoinCode.digest(raw)).first()
        if not code or not code.is_valid: raise ValidationError({"code": "This join code is invalid, expired, revoked, or fully used."})
        membership, created = ClubMembership.objects.get_or_create(club=code.club, user=request.user, defaults={"role_name": code.role_name, "permissions": code.permissions, "status": "active"})
        if not created: raise ValidationError({"code": "You already have a membership in this club."})
        code.uses += 1; code.save(update_fields=["uses"])
        log_activity(request.user, "membership.joined", f"Joined {code.club.name}", code.club, {"membership_id": membership.id})
    return Response(MembershipSerializer(membership).data, status=201)

def _can(request, club, permission):
    if not has_club_permission(request.user, club, permission): raise PermissionDenied()

class ScopedContentMixin:
    club_lookup = "club_pk"
    def get_club(self):
        club = Club.objects.filter(pk=self.kwargs.get(self.club_lookup)).first()
        if not club: raise ValidationError({"club": "Club not found."})
        return club

class EventViewSet(ScopedContentMixin, viewsets.ModelViewSet):
    serializer_class = EventSerializer
    def get_permissions(self):
        if self.action in ("list", "retrieve"): return [AllowAny()]
        return [IsAuthenticated()]
    def get_queryset(self):
        qs = Event.objects.filter(club_id=self.kwargs.get("club_pk"))
        club = Club.objects.filter(pk=self.kwargs.get("club_pk")).first()
        if self.request.method in ("GET", "HEAD", "OPTIONS") and (self.request.user.is_anonymous or not has_club_permission(self.request.user, club, "events.view")):
            qs = qs.filter(status="published")
        return qs
    def check_perm(self):
        perm = {"list":"events.view", "retrieve":"events.view", "create":"events.create", "update":"events.edit", "partial_update":"events.edit", "destroy":"events.delete"}.get(self.action, "events.edit")
        _can(self.request, self.get_club(), perm)
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if self.action in ("create", "update", "partial_update", "destroy") or request.user.is_authenticated: self.check_perm()
    def perform_create(self, serializer):
        obj=serializer.save(club=self.get_club(), created_by=self.request.user)
        log_activity(self.request.user,"event.created",f"Created event: {obj.title}",obj.club,{"event_id":obj.id})
    def perform_update(self, serializer):
        if serializer.validated_data.get("status") == "published": _can(self.request, self.get_club(), "events.publish")
        if serializer.validated_data.get("status") == "draft": _can(self.request, self.get_club(), "events.unpublish")
        previous_status=serializer.instance.status
        obj=serializer.save()
        log_activity(self.request.user,"event.updated",f"Updated event: {obj.title}",obj.club,{"event_id":obj.id})
        if obj.status=="cancelled" or (obj.status=="published" and previous_status!="published") or (obj.status=="published" and previous_status=="published"):
            kind="event_cancelled" if obj.status=="cancelled" else ("event_published" if previous_status!="published" else "event_updated")
            message=f"Event cancelled: {obj.title}" if obj.status=="cancelled" else (f"New event: {obj.title}" if previous_status!="published" else f"Event updated: {obj.title}")
            for member in obj.club.memberships.filter(status="active").select_related("user"):
                Notification.objects.create(user=member.user,club=obj.club,kind=kind,message=message)
    def perform_destroy(self, instance):
        log_activity(self.request.user,"event.deleted",f"Deleted event: {instance.title}",instance.club,{"event_id":instance.id})
        instance.delete()
    @action(detail=True, methods=["post"])
    def publish(self, request, club_pk=None, pk=None):
        _can(request, self.get_club(), "events.publish"); obj=self.get_object(); already_published=obj.status=="published"; obj.status="published"; obj.save(update_fields=["status", "updated_at"])
        log_activity(request.user,"event.published",f"Published event: {obj.title}",obj.club,{"event_id":obj.id})
        if not already_published:
            for member in obj.club.memberships.filter(status="active").select_related("user"):
                Notification.objects.create(user=member.user,club=obj.club,kind="event_published",message=f"New event: {obj.title}")
        return Response(self.get_serializer(obj).data)
    @action(detail=True, methods=["post"])
    def unpublish(self, request, club_pk=None, pk=None):
        _can(request, self.get_club(), "events.unpublish"); obj=self.get_object(); obj.status="draft"; obj.save(update_fields=["status", "updated_at"])
        log_activity(request.user,"event.unpublished",f"Unpublished event: {obj.title}",obj.club,{"event_id":obj.id})
        return Response(self.get_serializer(obj).data)

class AnnouncementViewSet(ScopedContentMixin, viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    def get_permissions(self):
        if self.action in ("list", "retrieve"): return [AllowAny()]
        return [IsAuthenticated()]
    def get_queryset(self):
        qs = Announcement.objects.filter(club_id=self.kwargs.get("club_pk"))
        club=Club.objects.filter(pk=self.kwargs.get("club_pk")).first()
        if self.request.user.is_anonymous or not has_club_permission(self.request.user, club, "announcements.view"): qs=qs.filter(status="published")
        return qs
    def initial(self, request, *args, **kwargs):
        super().initial(request,*args,**kwargs)
        if self.action in ("create","update","partial_update","destroy") or request.user.is_authenticated:
            perm={"list":"announcements.view","retrieve":"announcements.view","create":"announcements.create","update":"announcements.edit","partial_update":"announcements.edit","destroy":"announcements.delete"}.get(self.action,"announcements.edit")
            _can(request,self.get_club(),perm)
    def perform_create(self, serializer):
        obj=serializer.save(club=self.get_club(), author=self.request.user)
        log_activity(self.request.user,"announcement.created",f"Created announcement: {obj.title}",obj.club,{"announcement_id":obj.id})
    def perform_update(self, serializer):
        if serializer.validated_data.get("status")=="published": _can(self.request,self.get_club(),"announcements.publish")
        if serializer.validated_data.get("status")=="draft": _can(self.request,self.get_club(),"announcements.unpublish")
        if serializer.validated_data.get("status")=="archived": _can(self.request,self.get_club(),"announcements.delete")
        obj=serializer.save()
        log_activity(self.request.user,"announcement.updated",f"Updated announcement: {obj.title}",obj.club,{"announcement_id":obj.id})
        if obj.status=="published" and not obj.published_at:
            obj.published_at=timezone.now(); obj.save(update_fields=["published_at"])
            for member in obj.club.memberships.filter(status="active").select_related("user"):
                Notification.objects.create(user=member.user,club=obj.club,kind="announcement",message=f"New announcement: {obj.title}")
    def perform_destroy(self, instance):
        log_activity(self.request.user,"announcement.deleted",f"Deleted announcement: {instance.title}",instance.club,{"announcement_id":instance.id})
        instance.delete()
    @action(detail=True,methods=["post"])
    def publish(self,request,club_pk=None,pk=None):
        _can(request,self.get_club(),"announcements.publish"); obj=self.get_object(); already_published=obj.status=="published"; obj.status="published"; obj.published_at=timezone.now(); obj.save(update_fields=["status","published_at","updated_at"])
        log_activity(request.user,"announcement.published",f"Published announcement: {obj.title}",obj.club,{"announcement_id":obj.id})
        if not already_published:
            for member in obj.club.memberships.filter(status="active").select_related("user"): Notification.objects.create(user=member.user,club=obj.club,kind="announcement",message=f"New announcement: {obj.title}")
        return Response(self.get_serializer(obj).data)

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    def get_queryset(self): return Notification.objects.filter(user=self.request.user)
    @action(detail=True,methods=["post"])
    def read(self,request,pk=None):
        obj=self.get_object(); obj.read_at=timezone.now(); obj.save(update_fields=["read_at"]); return Response(self.get_serializer(obj).data)
    @action(detail=False,methods=["post"])
    def read_all(self,request):
        self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now()); return Response({"detail":"Notifications marked as read."})

class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=UserSerializer; permission_classes=[IsAdminUser]
    def get_queryset(self):
        qs=User.objects.filter(is_staff=False,is_superuser=False).order_by("last_name","first_name","username")
        q=self.request.query_params.get("search")
        return qs.filter(Q(username__icontains=q)|Q(email__icontains=q)|Q(first_name__icontains=q)|Q(last_name__icontains=q)) if q else qs

class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=ActivitySerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser: return ActivityLog.objects.select_related("actor","club")
        clubs=ClubMembership.objects.filter(user=self.request.user,status="active").values_list("club_id",flat=True)
        return ActivityLog.objects.filter(club_id__in=clubs).select_related("actor","club")

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_view(request):
    user=request.user
    memberships=user.club_memberships.filter(status="active").select_related("club")
    clubs=[{"id":m.club_id,"name":m.club.name,"abbreviation":m.club.abbreviation,"category":m.club.category,"role_name":m.role_name,"permissions":m.permissions,"member_count":m.club.memberships.filter(status="active").count()} for m in memberships]
    club_ids=[m.club_id for m in memberships]
    events=Event.objects.filter(club_id__in=club_ids,status="published",starts_at__gte=timezone.now()).order_by("starts_at")[:10]
    announcements=Announcement.objects.filter(club_id__in=club_ids,status="published").order_by("-published_at")[:10]
    return Response({"clubs":clubs,"upcoming_events":EventSerializer(events,many=True).data,"announcements":AnnouncementSerializer(announcements,many=True).data,"notifications":NotificationSerializer(user.notifications.all()[:10],many=True).data})

@api_view(["GET"])
@permission_classes([AllowAny])
def permissions_catalog(request):
    return Response({group:[{"key":key,"label":key.split(".",1)[1].replace("_"," ").title()} for key in values] for group,values in PERMISSION_GROUPS.items()})

@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_stats(request):
    return Response({"total_clubs":Club.objects.filter(status="active").count(),"total_students":User.objects.filter(is_active=True,is_staff=False).count(),"total_memberships":ClubMembership.objects.filter(status="active").count(),"upcoming_events":Event.objects.filter(status="published",starts_at__gte=timezone.now()).count(),"recent_activity":ActivitySerializer(ActivityLog.objects.select_related("actor","club")[:10],many=True).data})

@api_view(["POST"])
@permission_classes([IsAdminUser])
def create_user(request):
    username=request.data.get("username","").strip(); email=request.data.get("email","").strip()
    if not username or not email: raise ValidationError({"detail":"Username and email are required."})
    if User.objects.filter(username__iexact=username).exists(): raise ValidationError({"username":"That username is already in use."})
    if User.objects.filter(email__iexact=email).exists(): raise ValidationError({"email":"That email is already in use."})
    password=request.data.get("password","")
    try: validate_password(password)
    except DjangoValidationError as e: raise ValidationError({"password":list(e.messages)})
    user=User.objects.create_user(username=username,email=email,password=password,first_name=request.data.get("first_name","")[:150],last_name=request.data.get("last_name","")[:150])
    log_activity(request.user,"user.created",f"Created account for {username}")
    return Response(UserSerializer(user).data,status=201)

@api_view(["POST"])
@permission_classes([IsAdminUser])
def create_club_account(request):
    form=AdminClubAccountSerializer(data=request.data); form.is_valid(raise_exception=True); data=form.validated_data
    username=data["username"].strip(); email=data["email"].strip(); password=data["password"]
    role_name=data["role_name"].strip(); permissions=data["permissions"]; club=data["club"]
    if not username or not role_name: raise ValidationError({"detail":"Username and role are required."})
    if User.objects.filter(username__iexact=username).exists(): raise ValidationError({"username":"That username is already in use."})
    if User.objects.filter(email__iexact=email).exists(): raise ValidationError({"email":"That email is already in use."})
    try: validate_password(password)
    except DjangoValidationError as e: raise ValidationError({"password":list(e.messages)})
    with transaction.atomic():
        user=User.objects.create_user(username=username,email=email,password=password,first_name=data["first_name"].strip(),last_name=data["last_name"].strip())
        membership=ClubMembership.objects.create(club=club,user=user,role_name=role_name[:64],permissions=sorted(set(permissions)))
        log_activity(request.user,"club_account.created",f"Created {username} account for {club.name}",club,{"membership_id":membership.id,"user_id":user.id})
    return Response({"user":UserSerializer(user).data,"membership":MembershipSerializer(membership).data},status=201)
