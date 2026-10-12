from django.urls import path

from . import views

urlpatterns = [
    path("new/", views.expense_create, name="expense_create"),
    path("<int:pk>/", views.expense_detail, name="expense_detail"),
    path("<int:pk>/edit/", views.expense_edit, name="expense_edit"),
    path("<int:pk>/delete/", views.expense_delete, name="expense_delete"),
]