from django.urls import path

from . import views

urlpatterns = [
    path("", views.search, name="search"),
    path("entities/<int:entity_id>/", views.entity_detail, name="entity_detail"),
]
