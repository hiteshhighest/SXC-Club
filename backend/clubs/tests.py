from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Club, ClubMembership, JoinCode, Event, Announcement, ActivityLog

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
        self.client.get("/api/csrf/")
        blocked=self.client.post("/api/auth/login/",{"username":"student","password":"StrongPass123!"},format="json")
        self.assertEqual(blocked.status_code,403)
        token=self.client.cookies["csrftoken"].value
        allowed=self.client.post("/api/auth/login/",{"username":"student","password":"StrongPass123!"},format="json",HTTP_X_CSRFTOKEN=token)
        self.assertEqual(allowed.status_code,200)
        self.assertEqual(self.client.get("/api/auth/me/").status_code,200)
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
    def test_join_code_permissions_duplicate_expiry_revoke_and_usage(self):
        self.login(self.admin,"StrongPass123!")
        response=self.client.post("/api/join-codes/create/",{"club":self.club.id,"role_name":"President","permissions":["events.create"],"max_uses":1},format="json")
        self.assertEqual(response.status_code,201); code=response.data["code"]
        self.client.logout(); self.login(self.student,"StrongPass123!")
        redeemed=self.client.post("/api/join-codes/redeem/",{"code":code},format="json")
        self.assertEqual(redeemed.status_code,201); self.assertEqual(redeemed.data["role_name"],"President"); self.assertEqual(redeemed.data["permissions"],["events.create"])
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
    def test_event_announcement_view_permissions_and_published_feed(self):
        Event.objects.create(club=self.club,title="Public event",starts_at=timezone.now()+timedelta(days=1),status="published",created_by=self.admin)
        Event.objects.create(club=self.other,title="Private draft",starts_at=timezone.now()+timedelta(days=1),status="draft",created_by=self.admin)
        response=self.client.get(f"/api/clubs/{self.club.id}/events/")
        self.assertEqual(response.status_code,200); self.assertEqual(len(response.data["results"]),1)
        Announcement.objects.create(club=self.club,title="News",content="Hello",status="draft",author=self.admin)
        self.assertEqual(len(self.client.get(f"/api/clubs/{self.club.id}/announcements/").data["results"]),0)
