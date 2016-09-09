#!/usr/bin/env python
# -*- coding: utf-8 -*-

import click
import signal

from netkit.stream import Stream, LOCK_MODE_NONE
from netkit.box import Box

import time
import socket
from multiprocessing import Process, Value, Lock as ProcessLock
from threading import Lock as ThreadLock
from threading import Thread


class WSClientStream(object):
    """
    websocket的封装
    """

    def __init__(self, sock):
        self.sock = sock

    def write(self, data):
        from websocket import ABNF
        return self.sock.send(data, ABNF.OPCODE_BINARY)

    def read_with_checker(self, *args, **kwargs):
        return self.sock.recv()

    def close(self, *args, **kwargs):
        return self.sock.close(*args, **kwargs)


class ProcessWorker(object):
    """
    进程worker
    """
    # 线程间锁
    thread_lock = None
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

    def __init__(self, concurrent, reps, url, msg_cmd, timeout, share_result):
        self.thread_lock = ThreadLock()
        self.stream_checker = Box().check

        self.concurrent = concurrent
        self.reps = reps
        self.url = url
        self.msg_cmd = msg_cmd
        self.timeout = timeout
        self.share_result = share_result

    def make_stream(self):
        if self.url.startswith('ws://'):
            import websocket
            s = websocket.create_connection(self.url)
            stream = WSClientStream(s)
        else:
            host, port = self.url.split(':')
            address = (host, int(port))
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(address)
            s.settimeout(self.timeout)
            stream = Stream(s, lock_mode=LOCK_MODE_NONE)

        return stream

    def thread_worker(self, worker_idx):
        try:
            stream = self.make_stream()
        except:
            # 相当于说这个根本没有发起请求，所以在请求量上就没有加上，所以在失败上也就不统计了
            click.secho('thread_worker[%s] socket connect fail' % worker_idx, fg='red')
            return

        box = Box()
        box.cmd = self.msg_cmd

        send_buf = box.pack()

        transactions = successful_transactions = failed_transactions = 0

        for it in xrange(0, self.reps):
            transactions += 1
            stream.write(send_buf)
            try:
                recv_buf = stream.read_with_checker(self.stream_checker)
            except socket.timeout:
                failed_transactions += 1
                click.secho('thread_worker[%s] socket timeout' % worker_idx, fg='red')
                continue

            if not recv_buf:
                click.secho('thread_worker[%s] socket closed' % worker_idx, fg='red')
                failed_transactions += 1
                break
            else:
                successful_transactions += 1

        try:
            self.thread_lock.acquire()
            self.transactions += transactions
            self.successful_transactions += successful_transactions
            self.failed_transactions += failed_transactions
        finally:
            self.thread_lock.release()

    def run(self):
        self._handle_child_proc_signals()

        jobs = []

        begin_time = time.time()

        for it in xrange(0, self.concurrent):
            job = Thread(target=self.thread_worker, args=[it])
            job.daemon = True
            job.start()
            jobs.append(job)

        for job in jobs:
            job.join()

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


class ShockEcho(object):

    processes = None

    # 经过的时间
    share_elapsed_time = Value('f', 0)
    # 总请求，如果链接失败而没发送，不算在这里
    share_transactions = Value('i', 0)
    # 成功请求数
    share_successful_transactions = Value('i', 0)
    # 失败请求数，因为connect失败导致没发的请求也算在这里. 这3个值没有绝对的相等关系
    share_failed_transactions = Value('i', 0)

    def __init__(self, concurrent, reps, url, msg_cmd, timeout, process_count):
        self.processes = []
        self.concurrent = concurrent
        self.reps = reps
        self.url = url
        self.msg_cmd = msg_cmd
        self.timeout = timeout
        self.process_count = process_count

    def run(self):
        self._handle_parent_proc_signals()

        worker = ProcessWorker(self.concurrent, self.reps, self.url, self.msg_cmd, self.timeout, dict(
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
        return self.concurrent * self.reps * self.process_count

    @property
    def availability(self):
        if self.expected_transactions != 0:
            return 1.0 * self.successful_transactions / self.expected_transactions
        else:
            return 0
