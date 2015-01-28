*************************************
FoundationDB SQL Layer Django Adapter
*************************************

The `FoundationDB SQL Layer <https://github.com/FoundationDB/sql-layer>`_ is a full
SQL implementation built on the `FoundationDB <https://foundationdb.com>`_ storage
substrate. It provides high performance, multi-node scalability, fault-tolerance
and true multi-key ACID transactions.

This project provides a database backend for `Django <https://www.djangoproject.com>`_
and `South <http://south.aeracode.org>`_.


Supported SQL Layer Versions
============================

Version 2.0.0 is the recommended release for use with this adapter.

Releases back to 1.9.3 will work and any prior to that will not.


Supported Django Versions
=========================

Django versions 1.3 through 1.6 are fully functional. Support for the 1.7 series
will be added once it is stable.


Quick Start
===========

    Important:
    
    The `SQL Layer <https://github.com/FoundationDB/sql-layer>`_ must be installed and
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

