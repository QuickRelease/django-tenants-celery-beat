import json

from django.db import models
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import pytz
import timezone_field

from django.conf import settings
from django_tenants.utils import get_tenant_model, get_public_schema_name


class TenantTimezoneMixin(models.Model):
    timezone = timezone_field.TimeZoneField(
        default="UTC",
        display_GMT_offset=getattr(
            settings, "TENANT_TIMEZONE_DISPLAY_GMT_OFFSET", False
        ),
    )

    class Meta:
        abstract = True


class PeriodicTaskTenantLink(models.Model):
    tenant = models.ForeignKey(
        settings.TENANT_MODEL,
        on_delete=models.CASCADE,
        related_name="periodic_task_tenant_links",
    )
    periodic_task = models.OneToOneField(
        PeriodicTask,
        on_delete=models.CASCADE,
        related_name="periodic_task_tenant_link",
    )
    use_tenant_timezone = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.tenant} - {self.periodic_task}"

    def save(self, *args, **kwargs):
        """Make PeriodicTask tenant-aware.

        Inserts correct `_schema_name` for `self.tenant` and into
        `self.periodic_task.headers`.
        If `self.periodic_task` uses a crontab schedule and the tenant timezone should
        be used, the crontab is adjusted to use the timezone of the tenant.
        """
        update_fields = ["headers"]

        headers = json.loads(self.periodic_task.headers)
        headers["_schema_name"] = self.tenant.schema_name
        self.use_tenant_timezone = headers.pop(
            "_use_tenant_timezone", self.use_tenant_timezone
        )
        self.periodic_task.headers = json.dumps(headers)

        if self.periodic_task.crontab is not None:
            tz = self.tenant.timezone if self.use_tenant_timezone else pytz.utc
            schedule = self.periodic_task.crontab.schedule
            if schedule.tz != tz:
                schedule.tz = tz
                crontab = CrontabSchedule.from_schedule(schedule)
                if not crontab.id:
                    crontab.save()
                self.periodic_task.crontab = crontab
                update_fields.append("crontab")

        self.periodic_task.save(update_fields=update_fields)
        super().save(*args, **kwargs)

    @classmethod
    def align(cls, instance, **kwargs):
        """Ensure PeriodicTask `instance` is aligned with its tenant.

        If no PeriodicTaskTenantLink is attached, the headers dict determines how to
        create the tenant link (if not present or missing the `_schema_name` key, use
        `public`). Otherwise, the PeriodicTaskTenantLink is used to set the headers if
        they are not already set.
        """
        if hasattr(instance, "periodic_task_tenant_link"):
            # Ensure that the headers are present and aligned
            headers = json.loads(instance.headers)
            tenant_link = instance.periodic_task_tenant_link
            if (
                "_use_tenant_timezone" in headers
                or headers.get("_schema_name") != tenant_link.tenant.schema_name
            ):
                instance.periodic_task_tenant_link.save()
        else:
            headers = json.loads(instance.headers)
            schema_name = headers.get("_schema_name", get_public_schema_name())
            use_tenant_timezone = headers.get("_use_tenant_timezone", False)
            cls.objects.create(
                periodic_task=instance,
                # Assumes the public schema has been created already
                # As long as no fiddling goes on, these tenants should always exist
                tenant=get_tenant_model().objects.get(schema_name=schema_name),
                use_tenant_timezone=use_tenant_timezone,
            )


models.signals.post_save.connect(PeriodicTaskTenantLink.align, sender=PeriodicTask)
