from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='main:index', permanent=False)),
    path('main/', include(('main.urls', 'main'), namespace='main')),
    path('landing/', include(('landing.urls', 'landing'), namespace='landing')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
