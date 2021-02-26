import json
from unittest.mock import patch

import pytz
from django.test import TestCase

from tenancy.models import Tenant
from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule


class PeriodicTaskTenantLink(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenants = Tenant.objects.bulk_create(
            [
                Tenant(name="Public", schema_name="public"),
                Tenant(
                    name="Tenant 1", schema_name="tenant1", timezone="Europe/London"
                ),
                Tenant(name="Tenant 2", schema_name="tenant2", timezone="US/Eastern"),
            ]
        )

    def assert_linked(self, periodic_task, tenant, use_tz):
        self.assertEqual(
            periodic_task.periodic_task_tenant_link.tenant,
            tenant,
            "Tenant link established",
        )
        self.assertEqual(
            json.loads(periodic_task.headers).get("_schema_name"),
            tenant.schema_name,
            "Schema name header matches tenant",
        )
        if use_tz:
            self.assertTrue(
                periodic_task.periodic_task_tenant_link.use_tenant_timezone,
                "Linked TZ flag is True",
            )
            self.assertEqual(
                periodic_task.crontab.schedule.tz,
                pytz.timezone(tenant.timezone),
                "Crontab TZ matches the tenant's TZ",
            )
        else:
            self.assertFalse(
                periodic_task.periodic_task_tenant_link.use_tenant_timezone,
                "Linked TZ flag is False",
            )
            self.assertEqual(
                periodic_task.crontab.schedule.tz,
                pytz.utc,
                "Crontab TZ is the default (UTC)",
            )

    def test_align_new(self):
        """Align classmethod should create new object with correct properties."""
        crontab = CrontabSchedule.objects.create(hour="0")

        with self.subTest("Tenant using TZ"):
            periodic_task = PeriodicTask.objects.create(
                name="tenant_tz",
                task="test_task",
                crontab=crontab,
                headers=json.dumps(
                    {"_schema_name": "tenant1", "_use_tenant_timezone": True}
                ),
            )
            self.assert_linked(periodic_task, self.tenants[1], True)

        with self.subTest("Tenant"):
            periodic_task = PeriodicTask.objects.create(
                name="tenant",
                task="test_task",
                crontab=crontab,
                headers=json.dumps(
                    {"_schema_name": "tenant1", "_use_tenant_timezone": False}
                ),
            )
            self.assert_linked(periodic_task, self.tenants[1], False)

        with self.subTest("Public"):
            periodic_task = PeriodicTask.objects.create(
                name="public",
                task="test_task",
                crontab=crontab,
                headers=json.dumps(
                    {"_schema_name": "public", "_use_tenant_timezone": False}
                ),
            )
            self.assert_linked(periodic_task, self.tenants[0], False)

        with self.subTest("Extra headers"):
            periodic_task = PeriodicTask.objects.create(
                name="extra",
                task="test_task",
                crontab=crontab,
                headers=json.dumps(
                    {
                        "extra": "header",
                        "_schema_name": "public",
                        "_use_tenant_timezone": False,
                    }
                ),
            )
            self.assertEqual(
                json.loads(periodic_task.headers).get("extra"),
                "header",
                "Extra headers are left alone",
            )
            self.assert_linked(periodic_task, self.tenants[0], False)

        with self.subTest("Missing headers"):
            periodic_task = PeriodicTask.objects.create(
                name="missing", task="test_task", crontab=crontab
            )
            self.assert_linked(periodic_task, self.tenants[0], False)

    def test_align_existing(self):
        """Align classmethod should call save if PeriodicTask headers dictate.

        Saving should occur if and only if:
        - _schema_name does not match the linked tenant
        - _use_tenant_timezone is in the headers dict
        """
        periodic_task = PeriodicTask.objects.create(
            name="test",
            task="test_task",
            crontab=CrontabSchedule.objects.create(),
        )
        with patch(
            "django_tenants_celery_beat.models.PeriodicTaskTenantLink.save"
        ) as link_save:
            with self.subTest("No change"):
                periodic_task.save()
                self.assertFalse(link_save.called)

            headers = {"_schema_name": "tenant1"}
            with self.subTest("Change Tenant"):
                periodic_task.headers = json.dumps(headers)
                periodic_task.save()
                self.assertTrue(link_save.called_once)

            headers["_use_tenant_timezone"] = True
            with self.subTest("Change TZ"):
                periodic_task.headers = json.dumps(headers)
                periodic_task.save()
                self.assertTrue(link_save.called_once)

    def test_save(self):
        """Save method should set timezone flag and update linked PeriodicTask.

        - Set _schema_name header on PeriodicTask based on self.tenant.schema_name
        - Set self.use_tenant_timezone based on _use_tenant_timezone PeriodicTask header
        - Remove _use_tenant_timezone header on PeriodicTask
        - If PeriodicTask uses a CrontabSchedule and the timezone does not match, the
          CrontabSchedule should be updated.
        """
        periodic_task = PeriodicTask.objects.create(
            name="test_task",
            task="test_task",
            interval=IntervalSchedule.objects.create(
                every=2, period=IntervalSchedule.DAYS
            ),
            headers=json.dumps(
                {"_schema_name": "public", "_use_tenant_timezone": False}
            ),
        )

        periodic_task.periodic_task_tenant_link.tenant = self.tenants[1]
        periodic_task.periodic_task_tenant_link.save(update_fields=["tenant"])
        periodic_task.refresh_from_db()

        self.assertEqual(
            json.loads(periodic_task.headers).get("_schema_name"),
            self.tenants[1].schema_name,
            "Schema name header is updated to match tenant",
        )

        crontab = CrontabSchedule.objects.create(hour=12)
        periodic_task.interval = None
        periodic_task.crontab = crontab
        periodic_task.save()
        periodic_task.refresh_from_db()

        self.assertEqual(
            periodic_task.crontab.schedule.tz,
            pytz.utc,
            "Crontab TZ shouldn't match tenant",
        )

        periodic_task.periodic_task_tenant_link.use_tenant_timezone = True
        periodic_task.periodic_task_tenant_link.save(
            update_fields=["use_tenant_timezone"]
        )
        periodic_task.refresh_from_db()
        tz_crontab = periodic_task.crontab

        self.assertEqual(
            tz_crontab.schedule.tz,
            pytz.timezone(self.tenants[1].timezone),
            "TZ updated to match tenant",
        )
        self.assertNotEqual(crontab.id, tz_crontab.id, "New TZ aware crontab created")

        periodic_task.headers = json.dumps({"_use_tenant_timezone": False})
        periodic_task.save()
        periodic_task.refresh_from_db()

        self.assertFalse(
            "_use_tenant_timezone" in json.loads(periodic_task.headers),
            "Use tenant timezone header removed",
        )
        self.assertFalse(
            periodic_task.periodic_task_tenant_link.use_tenant_timezone,
            "Header overrides model field",
        )
        self.assertEqual(
            periodic_task.crontab.id, crontab.id, "Existing crontab reused"
        )

        periodic_task.periodic_task_tenant_link.use_tenant_timezone = True
        periodic_task.periodic_task_tenant_link.save(
            update_fields=["use_tenant_timezone"]
        )
        periodic_task.refresh_from_db()

        self.assertEqual(
            periodic_task.crontab.id, tz_crontab.id, "Existing TZ aware crontab reused"
        )
