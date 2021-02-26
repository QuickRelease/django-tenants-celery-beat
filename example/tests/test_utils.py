from celery.schedules import crontab
from django.test import TestCase

from django_tenants_celery_beat.utils import generate_beat_schedule
from tenancy.models import Tenant


class GenerateBeatScheduleTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Tenant.objects.bulk_create(
            [
                Tenant(name="Tenant 1", schema_name="tenant1", timezone="Europe/London"),
                Tenant(name="Tenant 2", schema_name="tenant2", timezone="US/Eastern"),
            ]
        )

    def test_public(self):
        expected = {
            "task_name": {
                "task": "core.tasks.test_task",
                "schedule": crontab(),
                "options": {
                    "headers": {"_schema_name": "public", "_use_tenant_timezone": False}
                }
            }
        }
        beat_schedule = generate_beat_schedule(
            {
                "task_name": {
                    "task": "core.tasks.test_task",
                    "schedule": crontab(),
                    "tenancy_options": {
                        "public": True,
                        "all_tenants": False,
                        "use_tenant_timezone": False,
                    }
                },
            }
        )
        self.assertEqual(beat_schedule, expected)

    def test_all_tenants(self):
        expected = {
            "tenant1: task_name": {
                "task": "core.tasks.test_task",
                "schedule": crontab(day_of_month=1),
                "options": {"headers": {"_schema_name": "tenant1", "_use_tenant_timezone": False}}
            },
            "tenant2: task_name": {
                "task": "core.tasks.test_task",
                "schedule": crontab(day_of_month=1),
                "options": {"headers": {"_schema_name": "tenant2", "_use_tenant_timezone": False}}
            }
        }
        beat_schedule = generate_beat_schedule(
            {
                "task_name": {
                    "task": "core.tasks.test_task",
                    "schedule": crontab(day_of_month=1),
                    "tenancy_options": {
                        "public": False,
                        "all_tenants": True,
                        "use_tenant_timezone": False,
                    }
                },
            }
        )
        self.assertEqual(beat_schedule, expected)

    def test_public_all_tenants(self):
        expected = {
            "task_name": {
                "task": "core.tasks.test_task",
                "schedule": crontab(day_of_month=1),
                "options": {
                    "headers": {
                        "_schema_name": "public", "_use_tenant_timezone": False
                    }
                }
            },
            "tenant1: task_name": {
                "task": "core.tasks.test_task",
                "schedule": crontab(day_of_month=1),
                "options": {
                    "headers": {
                        "_schema_name": "tenant1", "_use_tenant_timezone": False
                    }
                }
            },
            "tenant2: task_name": {
                "task": "core.tasks.test_task",
                "schedule": crontab(day_of_month=1),
                "options": {
                    "headers": {
                        "_schema_name": "tenant2", "_use_tenant_timezone": False
                    }
                }
            }
        }
        beat_schedule = generate_beat_schedule(
            {
                "task_name": {
                    "task": "core.tasks.test_task",
                    "schedule": crontab(day_of_month=1),
                    "tenancy_options": {
                        "public": True,
                        "all_tenants": True,
                        "use_tenant_timezone": False,
                    }
                },
            }
        )
        self.assertEqual(beat_schedule, expected)

    def test_use_tenant_timezone(self):
        expected = {
            "tenant1: task_name": {
                "task": "core.tasks.test_task",
                "schedule": crontab(0, 1),
                "options": {
                    "headers": {
                        "_schema_name": "tenant1", "_use_tenant_timezone": True
                    }
                }
            },
            "tenant2: task_name": {
                "task": "core.tasks.test_task",
                "schedule": crontab(0, 1),
                "options": {
                    "headers": {
                        "_schema_name": "tenant2", "_use_tenant_timezone": True
                    }
                }
            }
        }
        beat_schedule = generate_beat_schedule(
            {
                "task_name": {
                    "task": "core.tasks.test_task",
                    "schedule": crontab(0, 1),
                    "tenancy_options": {
                        "public": False,
                        "all_tenants": True,
                        "use_tenant_timezone": True,
                    }
                },
            }
        )
        self.assertEqual(beat_schedule, expected)
