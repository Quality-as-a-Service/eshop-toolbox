from django.contrib import admin
from django.urls import path, include
from gpt.views import gpt_dashboard_view, gpt_upload_view, gpt_action_view, gpt_completition_download, gpt_manual_view

urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),
    path('auth/', include('django.contrib.auth.urls')),
    path('', gpt_dashboard_view, name='home'),
    path('modules/gpt/dashboard', gpt_dashboard_view, name='gpt-dashboard'),
    path('modules/gpt/upload', gpt_upload_view, name='gpt-upload'),
    path('modules/gpt/action', gpt_action_view, name='gpt-action'),
    path('modules/gpt/export', gpt_completition_download, name='gpt-export'),
    path('modules/gpt/manual', gpt_manual_view, name='gpt-manual'),
]
