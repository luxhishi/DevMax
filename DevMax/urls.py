from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='main:index', permanent=False)),
    path('main/', include(('main.urls', 'main'), namespace='main')),
    path('landing/', include(('landing.urls', 'landing'), namespace='landing')),
    path('admin/', admin.site.urls),
]
