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
