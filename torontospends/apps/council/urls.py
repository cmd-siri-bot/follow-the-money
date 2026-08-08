from django.urls import path

from . import views

urlpatterns = [
    path("council/", views.search, name="council_search"),
]
