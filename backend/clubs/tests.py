from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Club, ClubMembership, JoinCode, Event, Announcement, ActivityLog, Notification

User=get_user_model()

class PlatformAPITests(TestCase):
    def setUp(self):
        self.client=APIClient(enforce_csrf_checks=True)
        self.admin=User.objects.create_superuser("admin","admin@sxc.test","StrongPass123!")
        self.student=User.objects.create_user("student","student@sxc.test","StrongPass123!")
        self.club=Club.objects.create(name="Robotics Club",abbreviation="ROBO")
        self.other=Club.objects.create(name="Drama Club",abbreviation="DRAMA")
    def login(self,user,password):
        self.client.get("/api/csrf/"); token=self.client.cookies["csrftoken"].value
        self.client.credentials(HTTP_X_CSRFTOKEN=token)
        return self.client.login(username=user.username,password=password)
    def test_authentication_and_admin_club_creation(self):
        self.assertTrue(self.login(self.student,"StrongPass123!"))
        denied=self.client.post("/api/clubs/",{"name":"New","abbreviation":"NEW"},format="json")
        self.assertEqual(denied.status_code,403)
        self.assertEqual(self.client.patch(f"/api/clubs/{self.club.id}/",{"status":"archived"},format="json").status_code,403)
        self.assertEqual(self.client.delete(f"/api/clubs/{self.club.id}/").status_code,403)
        self.client.logout(); self.login(self.admin,"StrongPass123!")
        created=self.client.post("/api/clubs/",{"name":"Art Club","abbreviation":"ART"},format="json")
        self.assertEqual(created.status_code,201)
    def test_admin_can_archive_restore_and_permanently_delete_club(self):
        self.login(self.admin,"StrongPass123!")
        archived=self.client.patch(f"/api/clubs/{self.club.id}/",{"status":"archived"},format="json")
        self.assertEqual(archived.status_code,200); self.club.refresh_from_db(); self.assertEqual(self.club.status,"archived")
        restored=self.client.patch(f"/api/clubs/{self.club.id}/",{"status":"active"},format="json")
        self.assertEqual(restored.status_code,200); self.club.refresh_from_db(); self.assertEqual(self.club.status,"active")
        ClubMembership.objects.create(club=self.club,user=self.student)
        Event.objects.create(club=self.club,title="Club event",starts_at=timezone.now()+timedelta(days=1))
        Announcement.objects.create(club=self.club,title="Club news",content="Notice")
        JoinCode.objects.create(club=self.club,role_name="Member",code_hash=JoinCode.digest("delete-test"),code_hint="TEST")
        deleted=self.client.delete(f"/api/clubs/{self.club.id}/")
        self.assertEqual(deleted.status_code,204); self.assertFalse(Club.objects.filter(pk=self.club.id).exists())
        self.assertTrue(ActivityLog.objects.filter(action="club.deleted",summary__contains="Robotics Club").exists())
        self.assertFalse(ClubMembership.objects.filter(club_id=self.club.id).exists())
        self.assertFalse(Event.objects.filter(club_id=self.club.id).exists())
        self.assertFalse(Announcement.objects.filter(club_id=self.club.id).exists())
        self.assertFalse(JoinCode.objects.filter(club_id=self.club.id).exists())
    def test_login_requires_csrf_and_works_with_token(self):
        token_response=self.client.get("/api/csrf/")
        self.assertEqual(token_response.status_code,200)
        self.assertTrue(token_response.data.get("csrfToken"))
        blocked=self.client.post("/api/auth/login/",{"username":"student","password":"StrongPass123!"},format="json")
        self.assertEqual(blocked.status_code,403)
        token=token_response.data["csrfToken"]
        allowed=self.client.post("/api/auth/login/",{"username":"student","password":"StrongPass123!"},format="json",HTTP_X_CSRFTOKEN=token)
        self.assertEqual(allowed.status_code,200)
        self.assertEqual(self.client.get("/api/auth/me/").status_code,200)
    @override_settings(
        CORS_ALLOWED_ORIGINS=["https://sxc-clubs.vercel.app"],
        CSRF_TRUSTED_ORIGINS=["https://sxc-clubs.vercel.app"],
        SESSION_COOKIE_SAMESITE="None", CSRF_COOKIE_SAMESITE="None",
        SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True,
    )
    def test_cross_origin_frontend_can_bootstrap_csrf_and_use_session_login(self):
        origin="https://sxc-clubs.vercel.app"
        token_response=self.client.get("/api/csrf/",HTTP_ORIGIN=origin,secure=True)
        self.assertEqual(token_response["Access-Control-Allow-Origin"],origin)
        self.assertEqual(token_response["Access-Control-Allow-Credentials"],"true")
        self.assertEqual(token_response.cookies["csrftoken"]["samesite"],"None")
        self.assertTrue(token_response.cookies["csrftoken"]["secure"])
        login_response=self.client.post("/api/auth/login/",{"username":"student","password":"StrongPass123!"},format="json",HTTP_ORIGIN=origin,HTTP_X_CSRFTOKEN=token_response.data["csrfToken"],secure=True)
        self.assertEqual(login_response.status_code,200)
        self.assertEqual(login_response.cookies["sessionid"]["samesite"],"None")
        self.assertTrue(login_response.cookies["sessionid"]["secure"])
    def test_student_and_admin_have_separate_login_paths(self):
        self.client.get("/api/csrf/"); token=self.client.cookies["csrftoken"].value
        student_denied=self.client.post("/api/auth/admin-login/",{"username":"student","password":"StrongPass123!"},format="json",HTTP_X_CSRFTOKEN=token)
        self.assertEqual(student_denied.status_code,403)
        admin_denied=self.client.post("/api/auth/login/",{"username":"admin","password":"StrongPass123!"},format="json",HTTP_X_CSRFTOKEN=token)
        self.assertEqual(admin_denied.status_code,403)
        admin_allowed=self.client.post("/api/auth/admin-login/",{"username":"admin","password":"StrongPass123!"},format="json",HTTP_X_CSRFTOKEN=token)
        self.assertEqual(admin_allowed.status_code,200)
        self.assertEqual(self.client.get("/api/auth/student/me/").status_code,403)
    def test_admin_creates_student_and_club_membership_atomically(self):
        self.login(self.admin,"StrongPass123!")
        response=self.client.post("/api/admin/accounts/",{"username":"newstudent","email":"newstudent@sxc.test","first_name":"New","last_name":"Student","password":"StrongPass123!","club":self.club.id,"role_name":"IT Head","permissions":["events.create"]},format="json")
        self.assertEqual(response.status_code,201)
        membership=ClubMembership.objects.get(user__username="newstudent",club=self.club)
        self.assertEqual(membership.role_name,"IT Head"); self.assertEqual(membership.permissions,["events.create"])
        self.assertFalse(membership.user.is_staff)
        self.client.logout(); self.assertTrue(self.client.login(username="newstudent",password="StrongPass123!"))
        self.assertEqual(self.client.get("/api/auth/student/me/").status_code,200)
        self.assertEqual(self.client.get("/api/auth/admin/me/").status_code,403)
    def test_admin_can_create_student_without_club_membership(self):
        self.login(self.admin,"StrongPass123!")
        response=self.client.post("/api/admin/accounts/",{"username":"unassigned","email":"unassigned@sxc.test","first_name":"Una","last_name":"Assigned","password":"StrongPass123!"},format="json")
        self.assertEqual(response.status_code,201)
        self.assertIsNone(response.data["membership"])
        self.assertTrue(User.objects.filter(username="unassigned",is_staff=False).exists())
        self.assertFalse(ClubMembership.objects.filter(user__username="unassigned").exists())
    def test_admin_deletes_student_accounts_and_preserves_authored_content(self):
        membership=ClubMembership.objects.create(club=self.club,user=self.student)
        Notification.objects.create(user=self.student,club=self.club,kind="test",message="Test notice")
        event=Event.objects.create(club=self.club,title="Student event",starts_at=timezone.now()+timedelta(days=1),created_by=self.student)
        announcement=Announcement.objects.create(club=self.club,title="Student news",content="Notice",author=self.student)
        self.login(self.admin,"StrongPass123!")
        response=self.client.delete(f"/api/admin/users/{self.student.id}/")
        self.assertEqual(response.status_code,204)
        self.assertFalse(User.objects.filter(pk=self.student.id).exists())
        self.assertFalse(ClubMembership.objects.filter(pk=membership.id).exists())
        self.assertFalse(Notification.objects.filter(user_id=self.student.id).exists())
        event.refresh_from_db(); announcement.refresh_from_db()
        self.assertIsNone(event.created_by); self.assertIsNone(announcement.author)
        self.assertTrue(ActivityLog.objects.filter(action="user.deleted",metadata__user_id=self.student.id).exists())
        self.assertEqual(self.client.delete(f"/api/admin/users/{self.admin.id}/").status_code,404)
    def test_admin_can_view_student_profile_but_students_cannot(self):
        self.student.profile.student_id="SXC-1024"; self.student.profile.phone="9800000000"; self.student.profile.save()
        membership=ClubMembership.objects.create(club=self.club,user=self.student,role_name="Secretary")
        self.login(self.admin,"StrongPass123!")
        response=self.client.get(f"/api/admin/users/{self.student.id}/")
        self.assertEqual(response.status_code,200)
        self.assertNotIn("student_id",response.data["profile"])
        self.assertNotIn("phone",response.data["profile"])
        self.assertTrue(any(item["role_name"]=="Secretary" for item in response.data["memberships"]))
        added=self.client.post(f"/api/admin/users/{self.student.id}/add-to-club/",{"club":self.other.id,"role_name":"Volunteer","permissions":["events.view"]},format="json")
        self.assertEqual(added.status_code,201)
        self.assertEqual(added.data["club_name"],self.other.name)
        self.assertEqual(added.data["role_name"],"Volunteer")
        duplicate=self.client.post(f"/api/admin/users/{self.student.id}/add-to-club/",{"club":self.other.id},format="json")
        self.assertEqual(duplicate.status_code,400)
        self.client.logout(); self.login(self.student,"StrongPass123!")
        self.assertEqual(self.client.get(f"/api/admin/users/{self.student.id}/").status_code,403)
    def test_join_code_permissions_duplicate_expiry_revoke_and_usage(self):
        self.login(self.admin,"StrongPass123!")
        response=self.client.post("/api/join-codes/create/",{"club":self.club.id,"role_name":"President","permissions":["events.create"],"max_uses":1},format="json")
        self.assertEqual(response.status_code,201); code=response.data["code"]
        self.client.logout(); self.login(self.student,"StrongPass123!")
        redeemed=self.client.post("/api/join-codes/redeem/",{"code":code},format="json")
        self.assertEqual(redeemed.status_code,201); self.assertEqual(redeemed.data["role_name"],"President"); self.assertEqual(redeemed.data["permissions"],["events.create"])
        self.assertEqual(redeemed.data["club_name"],self.club.name)
        self.assertEqual(self.client.post("/api/join-codes/redeem/",{"code":code},format="json").status_code,400)
    def test_join_code_expiry_and_revocation(self):
        expired=JoinCode.objects.create(club=self.club,role_name="Member",code_hash=JoinCode.digest("old"),code_hint="OLD",expires_at=timezone.now()-timedelta(days=1))
        self.login(self.student,"StrongPass123!")
        self.assertEqual(self.client.post("/api/join-codes/redeem/",{"code":"old"},format="json").status_code,400)
        self.client.logout();self.login(self.admin,"StrongPass123!")
        response=self.client.post("/api/join-codes/create/",{"club":self.club.id,"role_name":"Member"},format="json")
        self.client.post(f"/api/join-codes/{response.data['id']}/revoke/")
        self.client.logout();self.login(self.student,"StrongPass123!")
        self.assertEqual(self.client.post("/api/join-codes/redeem/",{"code":response.data["code"]},format="json").status_code,400)
    def test_club_isolation_and_permission_enforcement(self):
        ClubMembership.objects.create(club=self.club,user=self.student,role_name="Member",permissions=[])
        self.login(self.student,"StrongPass123!")
        denied=self.client.post(f"/api/clubs/{self.club.id}/events/",{"title":"Nope","starts_at":timezone.now().isoformat()},format="json")
        self.assertEqual(denied.status_code,403)
        hidden=self.client.get(f"/api/clubs/{self.other.id}/members/")
        self.assertEqual(hidden.status_code,403)
    def test_role_label_does_not_grant_permissions_and_delegation_is_limited(self):
        manager=User.objects.create_user("manager","manager@sxc.test","StrongPass123!")
        ClubMembership.objects.create(club=self.club,user=manager,role_name="President",permissions=["members.view","members.change_role","executives.permissions","join_codes.generate"])
        target=ClubMembership.objects.create(club=self.club,user=self.student,role_name="Member",permissions=[])
        self.login(manager,"StrongPass123!")
        changed=self.client.patch(f"/api/clubs/{self.club.id}/members/{target.id}/role/",{"role_name":"President"},format="json")
        self.assertEqual(changed.status_code,200); target.refresh_from_db(); self.assertEqual(target.permissions,[])
        escalation=self.client.patch(f"/api/clubs/{self.club.id}/members/{target.id}/permissions/",{"permissions":["events.publish"]},format="json")
        self.assertEqual(escalation.status_code,403)
        code=self.client.post("/api/join-codes/create/",{"club":self.club.id,"role_name":"Chair","permissions":["events.publish"]},format="json")
        self.assertEqual(code.status_code,403)
    def test_members_cannot_change_their_own_role_or_permissions(self):
        membership=ClubMembership.objects.create(club=self.club,user=self.student,role_name="Executive",permissions=["members.view","members.change_role","executives.permissions"])
        self.login(self.student,"StrongPass123!")
        role=self.client.patch(f"/api/clubs/{self.club.id}/members/{membership.id}/role/",{"role_name":"President"},format="json")
        permissions=self.client.patch(f"/api/clubs/{self.club.id}/members/{membership.id}/permissions/",{"permissions":["events.publish"]},format="json")
        self.assertEqual(role.status_code,403)
        self.assertEqual(permissions.status_code,403)
        membership.refresh_from_db()
        self.assertEqual(membership.role_name,"Executive")
        self.assertEqual(membership.permissions,["members.view","members.change_role","executives.permissions"])
    def test_event_announcement_view_permissions_and_published_feed(self):
        Event.objects.create(club=self.club,title="Public event",starts_at=timezone.now()+timedelta(days=1),status="published",created_by=self.admin)
        Event.objects.create(club=self.other,title="Private draft",starts_at=timezone.now()+timedelta(days=1),status="draft",created_by=self.admin)
        response=self.client.get(f"/api/clubs/{self.club.id}/events/")
        self.assertEqual(response.status_code,200); self.assertEqual(len(response.data["results"]),1)
        Announcement.objects.create(club=self.club,title="News",content="Hello",status="draft",author=self.admin)
        self.assertEqual(len(self.client.get(f"/api/clubs/{self.club.id}/announcements/").data["results"]),0)
    def test_admin_announcement_access_is_global_and_students_are_denied(self):
        first=Announcement.objects.create(club=self.club,title="First",content="One",author=self.admin)
        Announcement.objects.create(club=self.other,title="Second",content="Two",author=self.admin,status="draft")
        self.login(self.admin,"StrongPass123!")
        response=self.client.get("/api/admin/announcements/")
        self.assertEqual(response.status_code,200); self.assertEqual(response.data["count"],2)
        created=self.client.post("/api/admin/announcements/",{"club":self.other.id,"title":"College update","content":"Notice","status":"published"},format="json")
        self.assertEqual(created.status_code,201); self.assertEqual(created.data["club"],self.other.id)
        changed=self.client.patch(f"/api/admin/announcements/{first.id}/",{"title":"Updated title"},format="json")
        self.assertEqual(changed.status_code,200); self.assertEqual(changed.data["title"],"Updated title")
        self.client.logout(); self.login(self.student,"StrongPass123!")
        self.assertEqual(self.client.get("/api/admin/announcements/").status_code,403)
    def test_announcement_editor_can_edit_without_republishing(self):
        announcement=Announcement.objects.create(club=self.club,title="Published",content="Before",status="published",published_at=timezone.now(),author=self.admin)
        ClubMembership.objects.create(club=self.club,user=self.student,permissions=["announcements.view","announcements.edit"])
        self.login(self.student,"StrongPass123!")
        response=self.client.patch(f"/api/clubs/{self.club.id}/announcements/{announcement.id}/",{"title":"Updated","status":"published"},format="json")
        self.assertEqual(response.status_code,200); self.assertEqual(response.data["title"],"Updated")
    def test_club_chat_is_private_to_members_and_admins(self):
        self.assertEqual(self.client.get(f"/api/clubs/{self.club.id}/chat/").status_code,403)
        ClubMembership.objects.create(club=self.club,user=self.student)
        self.login(self.student,"StrongPass123!")
        self.assertEqual(self.client.get(f"/api/clubs/{self.club.id}/chat/").status_code,200)
        self.assertEqual(self.client.post(f"/api/clubs/{self.club.id}/chat/",{"content":"   "},format="json").status_code,400)
        sent=self.client.post(f"/api/clubs/{self.club.id}/chat/",{"content":"Hello club"},format="json")
        self.assertEqual(sent.status_code,201); self.assertEqual(sent.data["sender_id"],self.student.id)
        self.assertEqual(self.client.get(f"/api/clubs/{self.other.id}/chat/").status_code,403)
    def test_public_club_dashboard_handles_anonymous_visitors(self):
        response=self.client.get(f"/api/clubs/{self.club.id}/dashboard/")
        self.assertEqual(response.status_code,200); self.assertIsNone(response.data["my_membership"]); self.assertFalse(response.data["can_chat"])
    def test_members_can_read_published_content_without_private_view_permission(self):
        Event.objects.create(club=self.club,title="Public event",starts_at=timezone.now()+timedelta(days=1),status="published")
        Announcement.objects.create(club=self.club,title="Public note",content="Visible",status="published")
        ClubMembership.objects.create(club=self.club,user=self.student,permissions=[])
        self.login(self.student,"StrongPass123!")
        events=self.client.get(f"/api/clubs/{self.club.id}/events/")
        announcements=self.client.get(f"/api/clubs/{self.club.id}/announcements/")
        self.assertEqual(events.status_code,200); self.assertEqual(len(events.data["results"]),1)
        self.assertEqual(announcements.status_code,200); self.assertEqual(len(announcements.data["results"]),1)

class MediaServingTests(TestCase):
    def test_media_file_is_served_from_configured_root_and_path_traversal_is_rejected(self):
        with TemporaryDirectory() as media_root:
            image = Path(media_root) / "clubs" / "logo.png"
            image.parent.mkdir()
            image.write_bytes(b"test-image")
            outside = Path(media_root).parent / "private-media-test.txt"
            outside.write_text("private", encoding="utf-8")
            try:
                with override_settings(MEDIA_ROOT=media_root):
                    response = self.client.get("/media/clubs/logo.png")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(b"".join(response.streaming_content), b"test-image")
                    self.assertEqual(response["X-Content-Type-Options"], "nosniff")
                    blocked = self.client.get("/media/%2E%2E/private-media-test.txt")
                    self.assertEqual(blocked.status_code, 404)
            finally:
                outside.unlink(missing_ok=True)
