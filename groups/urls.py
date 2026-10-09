from django.urls import path

from . import views

urlpatterns = [
    path("", views.group_list, name="group_list"),
    path("new/", views.group_create, name="group_create"),
    path("join/<uuid:token>/", views.group_join, name="group_join"),
    path("<int:pk>/", views.group_detail, name="group_detail"),
    path("<int:pk>/leave/", views.group_leave, name="group_leave"),
    path("<int:pk>/delete/", views.group_delete, name="group_delete"),
    path("<int:pk>/regenerate-invite/", views.group_regenerate_invite, name="group_regenerate_invite"),
    path("<int:pk>/members/<int:membership_id>/remove/", views.member_remove, name="member_remove"),
]