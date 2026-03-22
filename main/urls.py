from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('post/<int:post_id>/comment/', views.post_comment, name='post_comment'),
    path('vote/post/<int:post_id>/', views.vote, name='vote_post'),
    path('vote/comment/<int:comment_id>/', views.vote, name='vote_comment'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('create-subthread/', views.create_subthread, name='create_subthread'),
    path('d/<path:name>/', views.subthread_detail, name='subthread_detail'),
]
