from django.contrib import admin
from django.db.models import F

from django_celery_beat.admin import PeriodicTaskAdmin
from django_celery_beat.models import PeriodicTask
from django_tenants.utils import get_public_schema_name

from django_tenants_celery_beat.models import PeriodicTaskTenantLink


class PeriodicTaskTenantLinkInline(admin.StackedInline):
    model = PeriodicTaskTenantLink
    can_delete = False

    def get_readonly_fields(self, request, obj=None):
        if request.tenant.schema_name == get_public_schema_name():
            return tuple()
        return ("tenant",)


class TenantPeriodicTaskAdmin(PeriodicTaskAdmin):
    list_display = (
        "__str__",
        "tenant",
        "enabled",
        "interval",
        "start_time",
        "last_run_at",
        "one_off",
    )
    list_filter = [
        ("periodic_task_tenant_link__tenant", admin.RelatedOnlyFieldListFilter),
        "enabled",
        "one_off",
        "task",
        "start_time",
        "last_run_at",
    ]
    inlines = [PeriodicTaskTenantLinkInline]

    def tenant(self, instance):
        return instance.periodic_task_tenant_link.tenant.name

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.tenant.schema_name != get_public_schema_name():
            qs = qs.filter(periodic_task_tenant_link__tenant=request.tenant)
        return qs.annotate(
            tenant=F("periodic_task_tenant_link__tenant__name")
        ).select_related("periodic_task_tenant_link__tenant")


admin.site.unregister(PeriodicTask)
admin.site.register(PeriodicTask, TenantPeriodicTaskAdmin)
