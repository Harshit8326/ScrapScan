from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')), # This tells Django to look in our app for routes
]