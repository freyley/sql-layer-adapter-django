DATABASES = {
    'default': {
        'ENGINE': 'django_fdbsql',
        'NAME': 'django_default',
    },
    'other': {
        'ENGINE': 'django_fdbsql',
        'NAME': 'django_other',
    }
}

# And also add 'south' to ALWAYS_INSTALLED_APPS in runtests.py
SKIP_SOUTH_TESTS = False
SOUTH_DATABASE_ADAPTERS = {
    'default': 'django_fdbsql.south_fdbsql'
}

SECRET_KEY = "django_tests_secret_key"

PASSWORD_HASHERS = (
    # Preferred, faster for tests
    'django.contrib.auth.hashers.MD5PasswordHasher',
    # Required by 1.4.x tests
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',
)

