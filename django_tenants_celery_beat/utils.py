from copy import deepcopy
import django
django.setup()  # noqa

from django_tenants.utils import get_tenant_model, get_public_schema_name


def generate_beat_schedule(beat_schedule_config):
    """Generate a tenant-aware beat_schedule.

    Pass in a beat_schedule as normal, but each entry can have an extra key
    `tenancy_options`, which is a dict with up to three Boolean keys:
        - `public`: run on the public schema
        - `all_tenants`: run on all tenant schemas
        - `use_tenant_timezone`: use the tenants' timezones for any crontab schedules

    For example, if you want the entry "everywhere" to run on the public schema, and
    on all tenant schemas at midday using their local timezone:
    ```
    generate_beat_schedule({
        "everywhere": {
            "task": "some_task",
            "schedule": crontab(hour=12),
            "tenancy_options": {
                "public": True,
                "all_tenants": True,
                "use_tenant_timezone": True,
            }
        }
    })
    ```
    This would generate the following beat_schedule:
    ```
    {
        "everywhere": { "task": "some_task", "schedule": crontab(hour=12) },
        "tenant1: everywhere": { "task": "some_task", "schedule": crontab(hour=12) },
        "tenant2: everywhere": { "task": "some_task", "schedule": crontab(hour=12) },
        ...
    }
    ```
    The timezone would then be set on the CrontabSchedule object that is later created
    when the beat_schedule is synced with the database.

    Args:
         beat_schedule_config: A valid beat_schedule dict with additional config
            describing how to handle tenancy options.

    Returns:
        A valid beat_schedule (assign it to `app.conf.beat_schedule`).
    """
    public_schema_name = get_public_schema_name()
    tenants = get_tenant_model().objects.exclude(schema_name=public_schema_name)
    beat_schedule = {}
    for name, config in beat_schedule_config.items():
        tenancy_options = config.pop("tenancy_options")
        if tenancy_options is None:
            # Missing `tenancy_options` key means the entry is ignored
            continue
        if tenancy_options.get("public", False):
            beat_schedule[name] = _set_schema_headers(
                deepcopy(config), public_schema_name
            )
        if tenancy_options.get("all_tenants", False):
            for tenant in tenants:
                _config = deepcopy(config)
                use_tenant_timezone = tenancy_options.get("use_tenant_timezone", False)
                beat_schedule[f"{tenant.schema_name}: {name}"] = _set_schema_headers(
                    _config, tenant.schema_name, use_tenant_timezone
                )
    return beat_schedule


def _set_schema_headers(config, schema_name, use_tenant_timezone=False):
    options = config.get("options", {})
    headers = options.get("headers", {})
    headers["_schema_name"] = schema_name
    headers["_use_tenant_timezone"] = use_tenant_timezone
    options["headers"] = headers
    config["options"] = options
    return config
