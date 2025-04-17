from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('applications/', include('applications.urls')),
    path('reviewer/', include('reviewer.urls')),
    path('documents/', include('documents.urls')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('queue/', include('queuing.urls', namespace='queuing')),
    path('', include('pwa.urls')),
    path('offline/', views.offline, name='offline'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)