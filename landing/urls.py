from django.urls import path
from .views import index, post_detail

urlpatterns = [
    path('', index, name='index'),
    path('post/<int:post_id>/', post_detail, name='post_detail'),
]