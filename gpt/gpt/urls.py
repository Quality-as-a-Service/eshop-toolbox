from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import TemplateView
from gpt.views import gpt_dashboard_view, gpt_upload_view

urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),
    path('auth/', include('django.contrib.auth.urls')),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('modules/gpt/dashboard', gpt_dashboard_view, name='gpt-dashboard'),
    path('modules/gpt/upload', gpt_upload_view, name='gpt-upload'),
]
