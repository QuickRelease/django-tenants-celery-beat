from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="django-tenants-celery-beat",
    version="0.1.0",
    author="David Vaughan",
    author_email="david.vaughan@quickrelease.co.uk",
    maintainer="Quick Release (Automotive) Ltd.",
    description="Support for celery beat in multitenant Django projects",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/QuickRelease/django-tenants-celery-beat",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: Django :: 2.0",
        "Framework :: Django :: 2.1",
        "Framework :: Django :: 2.2",
        "Framework :: Django :: 3.0",
        "Framework :: Django :: 3.1",
        "Framework :: Django :: 3.2",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
    ],
    keywords="django tenants celery beat multitenancy postgres postgresql",
    packages=[
        "django_tenants_celery_beat",
        "django_tenants_celery_beat.migrations",
    ],
    install_requires=[
        "Django>=2.0",
        "django-tenants>=3.0.0",
        "tenant-schemas-celery>=1.0.1",
        "django-celery-beat>=2.2.0",
        "django-timezone-field>=4.1.1",
    ],
    license="MIT",
)
