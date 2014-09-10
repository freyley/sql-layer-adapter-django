Running Tests
=============

#. ``git clone git@github.com:django/django.git``
#. ``git clone git@github.com:FoundationDB/sql-layer-adapter-django.git``
#. ``cd sql-layer-adapter-django/``
#. ``python setup.py sdist``
#. ``sudo pip install dist/django-fdbsql-*.tar.gz``
#. ``git apply --verbose --directory=../django/ test_support/django_x_y_z_tests.diff``
#. ``cp test_support/fdb_helper.py test_support/test_fdbsql.py ../django/tests/``
#. ``cd ../django/tests/``
#. ``export PYTHONPATH=..``
#. Start FoundationDB SQL Layer
#. ``python fdb_helper.py``

