from django.contrib import admin

from django_tenants.admin import TenantAdminMixin

from tenancy.models import Tenant


@admin.register(Tenant)
class ClientAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("name",)
