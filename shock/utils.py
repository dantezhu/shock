# -*- coding: utf-8 -*-

import sys

import constants


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


def import_module_or_string(src):
    """
    按照模块导入或者字符串导入
    :param src:
    :return:
    """
    from config import import_string
    return import_string(src) if isinstance(src, (str, unicode)) else src
