# -*- coding: utf-8 -*-

import sys


# Useful for very coarse version differentiation.
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = (str, )

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        else:
            raise value

else:
    string_types = (str, unicode)

    exec('''def reraise(tp, value, tb=None):
               raise tp, value, tb
        ''')
