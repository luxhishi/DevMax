# Dynamic Subthreads Implementation TODO (d/django format)

## Information Gathered:
- `landing/models.py`: Empty - ready for Subthread model
- `landing/views.py`: Hardcoded `suggested_subthreads`/`joined_subthreads` 
- navbar links → `/` (landing.views.index → main/templates/index.html)

## Plan:
1. **`landing/models.py`**: Add Subthread model (name, description, members, created_by)
2. **`landing/admin.py`**: Register Subthread for admin creation
3. **Migration**: `makemigrations` + `migrate`
4. **`landing/views.py`**: Replace hardcoded → `Subthread.objects.all()`
5. **`landing/urls.py`**: Add `create_subthread/` view
6. **Template**: Create subthread form (sidebar or + button)
7. **main/templates/components/subthread_card.html**: Use real data

## Dependent Files:
- `landing/models.py`, `landing/admin.py`, `landing/views.py`
- Migration files

## Followup:
```
python manage.py makemigrations landing
python manage.py migrate
python manage.py createsuperuser (if not done)
python manage.py runserver
```
Create subthreads in admin → appear on homepage.

Approve to start with model creation?

