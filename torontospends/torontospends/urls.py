"""
URL configuration for torontospends project.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.entities.urls')),
    path('', include('apps.budget.urls')),
    path('', include('apps.council.urls')),
]
