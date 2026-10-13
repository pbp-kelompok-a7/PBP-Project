from django.contrib import admin

from catalog.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "inventory_id", "rating", "created_at")