from django.contrib import admin
from django.urls import path, include
from gpt.views import gpt_dashboard_view, gpt_upload_view, gpt_dataset_action_view, gpt_completition_download, gpt_manual_view, test_db, reconnect_db

urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', gpt_dashboard_view, name='home'),
    path('modules/gpt/dashboard', gpt_dashboard_view, name='gpt-dashboard'),
    path('modules/gpt/upload', gpt_upload_view, name='gpt-upload'),
    path('modules/gpt/dataset/action',
         gpt_dataset_action_view, name='gpt-dataset-action'),
    path('modules/gpt/export', gpt_completition_download, name='gpt-export'),
    path('modules/gpt/manual', gpt_manual_view, name='gpt-manual'),
    path('db/test', test_db, name='db-test'),
    path('db/reconnect', reconnect_db, name='db-reconnect'),
]
