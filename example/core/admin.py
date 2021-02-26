from django.contrib import admin

from .models import Alignment, Character


@admin.register(Alignment)
class AlignmentAdmin(admin.ModelAdmin):
    pass


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("name", "alignment")
