from django.contrib import admin
from django.db.models import F

from django_celery_beat.admin import PeriodicTaskAdmin
from django_celery_beat.models import PeriodicTask
from django_tenants.utils import get_tenant_model, get_public_schema_name

from django_tenants_celery_beat.models import PeriodicTaskTenantLink


class PeriodicTaskTenantLinkInline(admin.StackedInline):
    model = PeriodicTaskTenantLink
    can_delete = False

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj is None:
            # Only for adding a new PeriodicTask
            formset.form.base_fields["tenant"].initial = request.tenant
            if not is_public(request):
                # Hide all other Tenants
                # Need to make the field non-readonly as otherwise the default value
                # is blank, and the PeriodicTask will be created with no Tenant, which
                # means it is then lost to the public schema
                formset.form.base_fields["tenant"].queryset = (
                    get_tenant_model().objects.filter(pk=request.tenant.pk)
                )
        return formset

    def get_readonly_fields(self, request, obj=None):
        if is_public(request):
            return tuple()
        if obj is None:
            # For new PeriodicTasks, we need to set the Tenant
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
        if not is_public(request):
            qs = qs.filter(periodic_task_tenant_link__tenant=request.tenant)
        return qs.annotate(
            tenant=F("periodic_task_tenant_link__tenant__name")
        ).select_related("periodic_task_tenant_link__tenant")


admin.site.unregister(PeriodicTask)
admin.site.register(PeriodicTask, TenantPeriodicTaskAdmin)


def is_public(request):
    return request.tenant.schema_name == get_public_schema_name()
