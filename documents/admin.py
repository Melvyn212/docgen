from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "doc_type", "term", "status", "created_at")
    list_filter = ("doc_type", "term", "status")
    search_fields = ("student__first_name", "student__last_name", "student__matricule")
