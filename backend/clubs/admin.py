from django.contrib import admin
from .models import UserProfile, Club, ClubMembership, JoinCode, Event, Announcement, Notification, ActivityLog, Permission

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin): list_display=("name","abbreviation","category","status"); search_fields=("name","abbreviation"); list_filter=("status","category")
@admin.register(ClubMembership)
class MembershipAdmin(admin.ModelAdmin): list_display=("user","club","role_name","status","joined_at"); list_filter=("status","club"); search_fields=("user__username","user__email","club__name")
@admin.register(JoinCode)
class JoinCodeAdmin(admin.ModelAdmin): list_display=("club","role_name","code_hint","uses","max_uses","expires_at","revoked_at"); readonly_fields=("code_hash","code_hint","uses")
@admin.register(Event)
class EventAdmin(admin.ModelAdmin): list_display=("title","club","starts_at","status"); list_filter=("status","club")
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin): list_display=("title","club","status","published_at"); list_filter=("status","club")
admin.site.register((UserProfile,Notification,ActivityLog,Permission))
