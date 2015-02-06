Running Tests
=============

#. Start FoundationDB SQL Layer
#. ``git clone git@github.com:django/django.git``
#. ``git clone git@github.com:FoundationDB/sql-layer-adapter-django.git``
#. ``cd django/``
#. ``git apply --verbose ../sql-layer-adapter-django/test_support/django_x_y_z_tests.diff``
#. ``cp ../sql-layer-adapter-django/test_support/{fdb_helper.py,test_fdbsql.py} tests/``
#. ``cd tests/``
#. ``export PYTHONPATH=..``
#. ``export DJANGO_SETTINGS_MODULE=test_fdbsql``
#. ``export PYTHONPATH=..:../../sql-layer-adapter-django``
#. ``python fdb_helper.py``

