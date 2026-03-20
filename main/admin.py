from django.contrib import admin
from .models import Subthread

@admin.register(Subthread)
class SubthreadAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'members', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']

