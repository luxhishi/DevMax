# DevMax Login Page Implementation TODO

## Steps to complete:

- [x] 1. Create `devmax/main/urls.py` with path('login/', views.login_view, name='login')
- [x] 2. Edit `devmax/DevMax/urls.py` to include main.urls at path('main/', include('main.urls'))
- [x] 3. Edit `devmax/main/views.py` to add login_view using Django auth
- [x] 4. Create `devmax/main/templates/registration/login.html` Tailwind form extending base.html
- [x] 5. [Optional] Update base.html navbar for user.is_authenticated state
- [x] 6. Test: createsuperuser, runserver, click Log in -> login -> redirect to /

## Followup:
- Check settings.py for auth apps
- python manage.py createsuperuser
- python manage.py runserver
