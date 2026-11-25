from rest_framework.permissions import BasePermission

PERMISSION_GROUPS = {
    "events": ["events.view", "events.create", "events.edit", "events.delete", "events.publish", "events.unpublish"],
    "announcements": ["announcements.view", "announcements.create", "announcements.edit", "announcements.delete", "announcements.publish", "announcements.unpublish"],
    "membership": ["members.view", "members.invite", "members.remove", "members.change_role"],
    "club": ["club.edit", "club.resources", "join_codes.generate", "join_codes.revoke", "executives.permissions"],
}
ALL_PERMISSIONS = {p for group in PERMISSION_GROUPS.values() for p in group}

def has_club_permission(user, club, permission):
    if club is None or not user.is_authenticated: return False
    if user.is_superuser or user.is_staff:
        return True
    membership = club.memberships.filter(user=user, status="active").first()
    return bool(membership and permission in membership.permissions)

class IsAuthenticatedOrReadOnlyPublic(BasePermission):
    def has_permission(self, request, view):
        return request.method in ("GET", "HEAD", "OPTIONS") or request.user.is_authenticated
