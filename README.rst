*************************************
FoundationDB SQL Layer Django Adapter
*************************************

`FoundationDB SQL Layer <https://github.com/FoundationDB/sql-layer>`_ is a full
SQL implementation built on the `FoundationDB <https://foundationdb.com>`_ storage
substrate. It provides high performance, multi-node scalability, fault-tolerance
and true multi-key ACID transactions.

This project provides a database backend for `Django <https://www.djangoproject.com>`_
and `South <http://south.aeracode.org>`_.


Supported SQL Layer Versions
============================

Versions >= 2.0 are recommended for use this adapter.


Supported Django Versions
=========================

Django versions 1.3 through 1.7 are fully functional.

Support for the 1.8 series will be added once it is stable.

    **Important**:

    The `default transaction behavior <https://docs.djangoproject.com/en/1.5/topics/db/transactions/>`_
    in versions prior to 1.6, including the 1.4 LTS release, is more challenging when using this
    adapter. With the default behavior of holding transactions open until a modifcation is made,
    a ``past_version`` error is highly likely. One of the alternative transaction management strategies
    (autocommit decorator, transaction context manager, or global deactivation) will need to be used.


Quick Start
===========

    **Important**:

    `SQL Layer <https://github.com/FoundationDB/sql-layer>`_ must be installed and
    running before attempting to use this adapter.


1. Install the adapter (*one* of the following):

   * Stable release::

     $ sudo pip install django-fdbsql

   * Latest development version::

     $ sudo pip install git+https://github.com/FoundationDB/sql-layer-adapter-django.git

2. Edit ``settings.py`` or ``settings_local.py``::

    DATABASES = {
        'default': {
          'ENGINE': 'django_fdbsql',
          'NAME': 'test_schema',
          ## Defaults
          'HOST': 'localhost',
          'PORT': '15432',
          'USER': 'django',
          'PASSWORD': '',
        }
    }

3. If you're using South for migrations (optional), add this to your settings as well::

    SOUTH_DATABASE_ADAPTERS = {
        'default': 'django_fdbsql.south_fdbsql'
    }

3. Sync your database::

    $ python manage.py syncdb


Adapter Options
===============

Two settings related to resetting sequences are allowed:

* ``supports_sequence_reset``

  * boolean - Defaults to ``False`` for Django compatibility. When ``True``, statements for resetting sequences are emitted (e.g. during unit tests, ``manage.py flush``).

* use_sequence_reset_function

  * boolean - Defaults to ``False`` for Django compatibility. When ``True``, use a stored procedure for resetting sequence values *higher* (useful in unit tests or syncing after loading fixtures). Sequences cannot be set lower.


Contributing
============

1. Fork
2. Branch
3. Commit
4. Pull Request


Contact
=======

* GitHub: http://github.com/FoundationDB/sql-layer-adapter-django
* Community: https://foundationdb.com/community
* IRC: #FoundationDB on irc.freenode.net


License
=======

| The MIT License (MIT)
| Copyright (c) 2013-2015 FoundationDB, LLC
| It is free software and may be redistributed under the terms specified
  in the LICENSE file.

