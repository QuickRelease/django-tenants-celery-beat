# django-tenants-celery-beat

Support for celery beat in multitenant Django projects. Schedule periodic tasks for a
specific tenant, with flexibility to run tasks with respect to each tenant's timezone. 

For use with [django-tenants](https://github.com/django-tenants/django-tenants) and
[tenant-schemas-celery](https://github.com/maciej-gol/tenant-schemas-celery).

Features:
- Configure static periodic tasks in `app.conf.beat_schedule` automatically for all
tenants, optionally in their own timezones
- Django admin modified to show and give you control over the tenant a task will run in
- Filter the admin based on tenants
- Tenant-level admin (e.g. tenant.domain.com) will only show tasks for that tenant

## Installation

Install via pip:
```commandline
pip install django-tenants-celery-beat
```

## Usage

Follow the instructions for [django-tenants](https://github.com/django-tenants/django-tenants)
and [tenant-schemas-celery](https://github.com/maciej-gol/tenant-schemas-celery).

In your `SHARED_APPS` (_not_ your `TENANT_APPS`):
```python
SHARED_APPS = [
    # ...
    "django_celery_results",
    "django_celery_beat",
    "django_tenants_celery_beat",
    # ...
]
```
Depending on your setup, you may also put `django_celery_results` in your `TENANT_APPS`.
(Assuming you have followed the instructions for
[django-tenants](https://github.com/django-tenants/django-tenants)
all your `SHARED_APPS` will also appear in your `INSTALLED_APPS`.)

`django-tenants-celery-beat` requires your `Tenant` model to have a `timezone` field in
order to control periodic task scheduling. To this end, we provide a `TenantTimezoneMixin`
that you should inherit from in your `Tenant` model, e.g.:
```python
from django_tenants.models import TenantMixin
from django_tenants_celery_beat.models import TenantTimezoneMixin

class Tenant(TenantTimezoneMixin, TenantMixin):
    pass
```
You can configure whether the timezones are displayed with the GMT offset, i.e.
`Australia/Sydney` vs. `GMT+11:00 Australia/Sydney`, using the setting
`TENANT_TIMEZONE_DISPLAY_GMT_OFFSET`. By default, the GMT offset is not shown.
(If you later change this setting, you will need to run `makemigrations` to see any effect.)

Ensure that `DJANGO_CELERY_BEAT_TZ_AWARE` is True (the default) for any timezone aware
scheduling to work. 

Once this has been done, you will need to run `makemigrations`. This will create the
necessary migrations for your `Tenant` model but also for the models that come with this
package. To apply the migrations, run:
```commandline
python manage.py migrate_schemas --shared
```

### Setting up a `beat_schedule`

For statically configured periodic tasks assigned via `app.conf.beat_schedule`, there
is a helper utility function to produce a valid tenant-aware `beat_schedule`. You can take
an existing `beat_schedule` and make minor modifications to achieve the desired behaviour.

The `generate_beat_schedule` function takes a dict that looks exactly like the usual
`beat_schedule` dict, but each task contains an additional entry with the key `tenancy_options`.
Here you can specify three things:
- Should the task run in the `public` schema?
- Should the task run on all tenant schemas?
- Should the task scheduling use the tenant's timezone?

All of these are False by default, so you only need to include them if you set them to True,
though you may prefer to keep them there to be explicit about your intentions. At least one
of the `public` or `all_tenants` keys must be True, otherwise the entry is ignored.
Additionally, if the `tenancy_option` key is missing from an entry, that entry will be ignored.

Example usage:
```python
app.conf.beat_schedule = generate_beat_schedule(
    {
        "tenant_task": {
            "task": "app.tasks.tenant_task",
            "schedule": crontab(minute=0, hour=12, day_of_week=1),
            "tenancy_options": {
                "public": False,
                "all_tenants": True,
                "use_tenant_timezone": True,
            }
        },
        "hourly_tenant_task": {
            "task": "app.tasks.hourly_tenant_task",
            "schedule": crontab(minute=0),
            "tenancy_options": {
                "public": False,
                "all_tenants": True,
                "use_tenant_timezone": False,
            }
        },
        "public_task": {
            "task": "app.tasks.tenant_task",
            "schedule": crontab(minute=0, hour=0, day_of_month=1),
            "tenancy_options": {
                "public": True,
                "all_tenants": False,
            }
        }
    }
)
```
This `beat_schedule` will actually produce an entry for each tenant with the schema name
as a prefix. For example, `tenant1: celery.backend_cleanup`. For public tasks, there is
no prefix added to the name.

This function also sets some AMQP message headers, which is how the schema and timezone
settings are configured.

#### Configuring `celery.backend_cleanup`

Note that in many cases, tasks should not be both run on the `public` schema and on all
tenant schemas, as the database tables are often very different. One example that most
likely should is the `celery.backend_cleanup` task that is automatically added. If you
do nothing with it, it will run only in the public schema, which may or may not suit your
needs. Assuming you have `django_celery_results` in `TENANT_APPS` you will need this task to
be run on all tenants, and if you also have it in `SHARED_APPS`, you will need it to run
on the `public` schema too. This task is also a case where you will likely want it to run
in the tenant's timezone so it always runs during a quiet time.

Using the utility function, this is how we could set up the `celery.backend_cleanup` task:
```python
from django_tenants_celery_beat.utils import generate_beat_schedule

# ...

app.conf.beat_schedule = generate_beat_schedule(
    {
        "celery.backend_cleanup": {
            "task": "celery.backend_cleanup",
            "schedule": crontab("0", "4", "*"),
            "options": {"expire_seconds": 12 * 3600},
            "tenancy_options": {
                "public": True,
                "all_tenants": True,
                "use_tenant_timezone": True,
            }
        }
    }
)
```
This will prevent the automatically created one being added, though the settings are
identical to the automatic one as of `django-celery-beat==2.2.0`. You could also set
`public` to False here for exactly the same resulting schedule, as the public one will
be automatically created by `django-celery-beat`.

### Modifying Periodic Tasks in the Django Admin

You can further manage periodic tasks in the Django admin.

The public schema admin will display the periodic tasks for each tenant as well as the
public tenant.

When on a tenant-level admin (e.g. `tenant.domain.com`), you can only see
the tasks for the given tenant, and any filters are hidden so as to not show a list of
tenants.

When editing a `PeriodicTask`, there is an inline form for the `OneToOneModel` added by
this package that connects a `PeriodicTask` to a `Tenant`. You can toggle the
`use_tenant_timezone` setting (but when restarting the beat service, the `beat_schedule`
will always take precedence). The tenant is shown as a read-only field, unless you are
on the public admin site, in which case you have the option edit the tenant. Editing the
tenant here will take precedence over the `beat_schedule`.
