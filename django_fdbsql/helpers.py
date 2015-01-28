# FoundationDB SQL Layer Adapter for Django
# Copyright (c) 2013-2014 FoundationDB, LLC

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from django import VERSION as DJANGO_VERSION

DJANGO_MAJ_MIN = DJANGO_VERSION[0:2]
DJANGO_GTEQ_1_4 = (DJANGO_MAJ_MIN >= (1,4))
DJANGO_GTEQ_1_5 = (DJANGO_MAJ_MIN >= (1,5))
DJANGO_GTEQ_1_6 = (DJANGO_MAJ_MIN >= (1,6))
DJANGO_GTEQ_1_7 = (DJANGO_MAJ_MIN >= (1,7))

if DJANGO_GTEQ_1_7:
    def fdb_test_setting(settings_dict, opt_name):
        return settings_dict['TEST'][opt_name]
else:
    def fdb_test_setting(settings_dict, opt_name):
        return settings_dict['TEST_' + opt_name]

if DJANGO_GTEQ_1_6:
    from django.db.backends import FieldInfo

    def fdb_field_info(tpl):
        return FieldInfo(*tpl)
else:
    def fdb_field_info(tpl):
        return tpl


if DJANGO_GTEQ_1_5:
    from django.utils.encoding import force_str as fdb_force_str
    from django.utils.six import reraise as fdb_reraise
else:
    from django.utils.encoding import smart_str

    fdb_force_str = smart_str

    def fdb_reraise(tp, value, tb=None):
        raise tp, value


if DJANGO_GTEQ_1_4:
    from django.utils.encoding import force_text as fdb_force_text
    from django.utils import timezone
    from django.utils.six import text_type as fdb_text_type
    from django.utils.six.moves import input as fdb_get_input

    fdb_tz_is_aware = timezone.is_aware

    def fdb_check_use_tz(s):
        return s.USE_TZ

else:
    from django.utils.encoding import smart_str as fdb_force_text

    timezone = None
    fdb_get_input = raw_input

    def fdb_tz_is_aware(value):
        return value.tzinfo is not None

    def fdb_text_type(value):
        return unicode(value)

    def fdb_check_use_tz(s):
        return False

