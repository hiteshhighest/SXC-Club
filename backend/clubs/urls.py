from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter
from .views import (login_view, admin_login_view, logout_view, me_view, student_me_view, admin_me_view, PasswordResetRequest, password_reset_confirm, ClubViewSet, MembershipViewSet,
    EventViewSet, AnnouncementViewSet, NotificationViewSet, AdminUserViewSet, ActivityViewSet,
    dashboard_view, permissions_catalog, admin_stats, create_user, create_club_account, create_join_code, list_join_codes, revoke_join_code, redeem_join_code)

router=DefaultRouter()
router.register("clubs",ClubViewSet,basename="club")
router.register("notifications",NotificationViewSet,basename="notification")
router.register("admin/users",AdminUserViewSet,basename="admin-user")
router.register("activity",ActivityViewSet,basename="activity")
nested=SimpleRouter()
nested.register(r"clubs/(?P<club_pk>[^/.]+)/members",MembershipViewSet,basename="club-members")
nested.register(r"clubs/(?P<club_pk>[^/.]+)/events",EventViewSet,basename="club-events")
nested.register(r"clubs/(?P<club_pk>[^/.]+)/announcements",AnnouncementViewSet,basename="club-announcements")
urlpatterns=[
    path("auth/login/",login_view),path("auth/admin-login/",admin_login_view),path("auth/logout/",logout_view),path("auth/me/",me_view),path("auth/student/me/",student_me_view),path("auth/admin/me/",admin_me_view),path("auth/password-reset/",PasswordResetRequest.as_view()),path("auth/password-reset/confirm/",password_reset_confirm),
    path("dashboard/",dashboard_view),path("permissions/",permissions_catalog),path("admin/stats/",admin_stats),path("admin/users/create/",create_user),path("admin/accounts/",create_club_account),
    path("join-codes/",list_join_codes),path("join-codes/create/",create_join_code),path("join-codes/<int:pk>/revoke/",revoke_join_code),path("join-codes/redeem/",redeem_join_code),
    path("",include(router.urls)),path("",include(nested.urls)),
]
