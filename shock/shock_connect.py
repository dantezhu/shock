# -*- coding: utf-8 -*-

import click
import signal

from netkit.box import Box
from netkit.contrib.tcp_client import TcpClient

import time
from multiprocessing import Process, Value, Lock as ProcessLock


class ProcessWorker(object):
    """
    进程worker
    """
    # 经过的时间
    elapsed_time = 0
    # 总请求，如果链接失败而没发送，不算在这里
    transactions = 0
    # 成功请求数
    successful_transactions = 0
    # 失败请求数，真实的发送了请求之后的报错才算在这里
    failed_transactions = 0
    # 进程间共享数据
    share_result = None

    def __init__(self, concurrent, url, timeout, share_result):
        self.stream_checker = Box().check

        self.concurrent = concurrent
        self.url = url
        self.timeout = timeout
        self.share_result = share_result

    def make_stream(self):
        host, port = self.url.split(':')
        address = (host, int(port))

        client = TcpClient(Box, address=address, timeout=self.timeout)
        client.connect()

        return client

    def run(self):
        self._handle_child_proc_signals()

        begin_time = time.time()

        # 要存起来，否则socket会自动释放
        client_list = []
        for it in xrange(0, self.concurrent):
            self.transactions += 1

            try:
                client_list.append(self.make_stream())
                self.successful_transactions += 1
            except KeyboardInterrupt:
                # 强制退出
                return
            except:
                click.secho('socket[%s] connect fail' % it, fg='red')
                self.failed_transactions += 1

        end_time = time.time()

        self.elapsed_time = end_time - begin_time

        try:
            self.share_result['lock'].acquire()
            self.share_result['elapsed_time'].value += self.elapsed_time
            self.share_result['transactions'].value += self.transactions
            self.share_result['successful_transactions'].value += self.successful_transactions
            self.share_result['failed_transactions'].value += self.failed_transactions
        finally:
            self.share_result['lock'].release()

    def _handle_child_proc_signals(self):
        # 不能用 signal.default_int_handler，停不了
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        # 即使对于SIGINT，SIG_DFL和default_int_handler也是不一样的，要是想要抛出KeyboardInterrupt，应该用default_int_handler
        # signal.signal(signal.SIGINT, signal.default_int_handler)


class ShockConnect(object):

    processes = None

    # 经过的时间
    share_elapsed_time = Value('f', 0)
    # 总请求，如果链接失败而没发送，不算在这里
    share_transactions = Value('i', 0)
    # 成功请求数
    share_successful_transactions = Value('i', 0)
    # 失败请求数，因为connect失败导致没发的请求也算在这里. 这3个值没有绝对的相等关系
    share_failed_transactions = Value('i', 0)

    def __init__(self, concurrent, url, timeout, process_count):
        self.processes = []
        self.concurrent = concurrent
        self.url = url
        self.timeout = timeout
        self.process_count = process_count

    def run(self):
        self._handle_parent_proc_signals()

        worker = ProcessWorker(self.concurrent, self.url, self.timeout, dict(
            lock=ProcessLock(),
            elapsed_time=self.share_elapsed_time,
            transactions=self.share_transactions,
            successful_transactions=self.share_successful_transactions,
            failed_transactions=self.share_failed_transactions,
        ))

        for it in xrange(0, self.process_count):
            proc = Process(target=worker.run)
            proc.daemon = True
            proc.start()
            self.processes.append(proc)

        for proc in self.processes:
            proc.join()

        # 平均
        self.share_elapsed_time.value = self.share_elapsed_time.value / self.process_count

    def _term_processes(self, *args):
        for proc in self.processes:
            if proc.is_alive():
                proc.terminate()

    def _handle_parent_proc_signals(self):
        signal.signal(signal.SIGTERM, self._term_processes)
        signal.signal(signal.SIGINT, self._term_processes)
        signal.signal(signal.SIGQUIT, self._term_processes)

    @property
    def elapsed_time(self):
        return self.share_elapsed_time.value

    @property
    def transactions(self):
        return self.share_transactions.value

    @property
    def successful_transactions(self):
        return self.share_successful_transactions.value

    @property
    def failed_transactions(self):
        return self.share_failed_transactions.value

    @property
    def transaction_rate(self):
        """
        每秒的请求数
        """
        if self.elapsed_time != 0:
            return 1.0 * self.transactions / self.elapsed_time
        else:
            return 0

    @property
    def response_time(self):
        """
        平均响应时间
        """
        if self.transactions != 0:
            return 1.0 * self.elapsed_time / self.transactions
        else:
            return 0

    @property
    def expected_transactions(self):
        """
        计划的请求数
        :return:
        """
        return self.concurrent * self.process_count

    @property
    def availability(self):
        if self.expected_transactions != 0:
            return 1.0 * self.successful_transactions / self.expected_transactions
        else:
            return 0
