from django.db import models

from django_tenants.models import DomainMixin, TenantMixin
from django_tenants_celery_beat.models import TenantTimezoneMixin


class Tenant(TenantTimezoneMixin, TenantMixin):
    name = models.CharField(max_length=100)
    created_on = models.DateField(auto_now_add=True)

    # default true, schema will be automatically created and synced when it is saved
    auto_create_schema = True

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    pass
