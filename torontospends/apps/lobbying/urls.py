from django.urls import path

from . import views

urlpatterns = [
    path("lobbying/", views.overview, name="lobbying_overview"),
]
