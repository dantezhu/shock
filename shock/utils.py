# -*- coding: utf-8 -*-

import sys

from . import constants
from .six import string_types, reraise


def make_proc_name(subtitle):
    """
    获取进程名称
    :param subtitle:
    :return:
    """
    proc_name = '[%s:%s] %s' % (
        constants.NAME,
        subtitle,
        ' '.join([sys.executable] + sys.argv)
    )

    return proc_name


def import_string(import_name, silent=False):
    """Imports an object based on a string.  This is useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If `silent` is True the return value will be `None` if the import fails.

    :param import_name: the dotted name for the object to import.
    :param silent: if set to `True` import errors are ignored and
                   `None` is returned instead.
    :return: imported object
    """
    # force the import name to automatically convert to strings
    # __import__ is not able to handle unicode strings in the fromlist
    # if the module is a package
    import_name = str(import_name).replace(':', '.')
    try:
        try:
            __import__(import_name)
        except ImportError:
            if '.' not in import_name:
                raise
        else:
            return sys.modules[import_name]

        module_name, obj_name = import_name.rsplit('.', 1)
        try:
            module = __import__(module_name, None, None, [obj_name])
        except ImportError:
            # support importing modules not yet set up by the parent module
            # (or package for that matter)
            module = import_string(module_name)

        try:
            return getattr(module, obj_name)
        except AttributeError as e:
            raise ImportError(e)

    except ImportError as e:
        if not silent:
            t, v, tb = sys.exc_info()
            reraise(t, v, tb)


def import_module_or_string(src):
    """
    按照模块导入或者字符串导入
    :param src:
    :return:
    """
    return import_string(src) if isinstance(src, string_types) else src
