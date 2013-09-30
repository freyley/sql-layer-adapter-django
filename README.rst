*************************************
FoundationDB SQL Layer Django Adapter
*************************************

The `FoundationDB SQL Layer <https://github.com/FoundationDB/sql-layer>`_ is a
full SQL implementation built upon the `FoundationDB <https://foundationdb.com>`_'s
storage substrate. It provides the same high performance, multi-node scalability,
fault-tolerance, and true multi-key ACID transactions.

This project provides a database backend for `Django <https://www.djangoproject.com>`_
and `South <http://south.aeracode.org>`_.


Supported Django Versions
=========================

Django versions 1.3, 1.4 and 1.5 are known to work and have been tested with sample
applications. However, this project is still in the alpha stages so there are most
likely cases that haven't been covered. Do let us know (see *Contact* section below)
if you run into any problems.


Quick Start
===========

1. Install the adapter::
    
    $ sudo pip install git+https://github.com/FoundationDB/sql-layer-adapter-django.git

2. Edit ``settings.py`` or ``settings_local.py``::
    
    DATABASES = {
        'default': {
          'ENGINE': 'django_fdbsql',
          'NAME': 'test_schema',
          ## Defaults
          #'HOST': 'localhost',
          #'PORT': '15432',
          #'USER': 'django_test',
          #'PASSWORD': '',
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
* Community: http://community.foundationdb.com
* IRC: #FoundationDB on irc.freenode.net


License
=======

| The MIT License (MIT)
| Copyright (c) 2013 FoundationDB, LLC
| It is free software and may be redistributed under the terms specified
  in the LICENSE file.

