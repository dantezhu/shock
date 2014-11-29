# -*- coding: utf-8 -*-

import click

from netkit.stream import Stream
from netkit.box import Box

import time
import socket
from multiprocessing import Pool
from thread import start_new_thread
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
    # 经过的时间
    elapsed_time = 0
    # 总请求，如果链接失败而没发送，不算在这里
    transactions = 0
    # 成功请求数
    successful_transactions = 0
    # 失败请求数，因为connect失败导致没发的请求也算在这里. 这3个值没有绝对的相等关系
    failed_transactions = 0

    def __init__(self, concurrent, reps, url, msg_cmd, socket_type):
        self.concurrent = concurrent
        self.reps = reps
        self.url = url
        self.msg_cmd = msg_cmd
        self.socket_type = socket_type
        self.stream_checker = Box().check
        self.stream_checker = Box().check

    def make_stream(self):
        if self.socket_type == 'socket':
            host, port = self.url.split(':')
            address = (host, int(port))
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(address)
            stream = Stream(s, use_gevent=True, lock_mode=0)
        else:
            import websocket
            s = websocket.create_connection(self.url)
            stream = WSClientStream(s)

        return stream

    def thread_worker(self, worker_idx):
        try:
            stream = self.make_stream()
        except:
            # 直接把所有的错误请求都加上
            self.failed_transactions += self.reps
            click.secho('thread_worker[%s] socket connect fail' % worker_idx, fg='red')
            return

        box = Box()
        box.cmd = self.msg_cmd

        send_buf = box.pack()
        for it in xrange(0, self.reps):
            self.transactions += 1
            stream.write(send_buf)
            recv_buf = stream.read_with_checker(self.stream_checker)
            if not recv_buf:
                click.secho('thread_worker[%s] socket closed' % worker_idx, fg='red')
                self.failed_transactions += 1
                break
            else:
                self.successful_transactions += 1

    def run(self):
        jobs = []

        begin_time = time.time()

        for it in xrange(0, self.concurrent):
            job = Thread(target=self.thread_worker, args=[it])
            job.start()
            job.daemon = Thread
            jobs.append(job)

        for job in jobs:
            job.join()

        end_time = time.time()

        self.elapsed_time = end_time - begin_time

        return dict(
            elapsed_time=self.elapsed_time,
            transactions=self.transactions,
            successful_transactions=self.successful_transactions,
            failed_transactions=self.failed_transactions,
        )


class Flood(object):

    # 经过的时间
    elapsed_time = 0
    # 总请求，如果链接失败而没发送，不算在这里
    transactions = 0
    # 成功请求数
    successful_transactions = 0
    # 失败请求数，因为connect失败导致没发的请求也算在这里. 这3个值没有绝对的相等关系
    failed_transactions = 0

    def __init__(self, concurrent, reps, url, msg_cmd, socket_type, process_count):
        self.concurrent = concurrent
        self.reps = reps
        self.url = url
        self.msg_cmd = msg_cmd
        self.socket_type = socket_type
        self.process_count = process_count

    def run(self):

        pool = Pool(processes=self.process_count)
        worker = ProcessWorker(self.concurrent_per_process, self.reps, self.url, self.msg_cmd, self.socket_type)
        result_list = pool.map(worker.run, [])

        for result in result_list:
            self.elapsed_time += result['elapsed_time']
            self.transactions += result['transactions']
            self.successful_transactions += result['successful_transactions']
            self.failed_transactions += result['failed_transactions']

        self.elapsed_time = float(self.elapsed_time) / self.process_count

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
    def plan_transactions(self):
        """
        计划的请求数
        :return:
        """
        return self.concurrent * self.reps

    @property
    def availability(self):
        if self.plan_transactions != 0:
            return 1.0 * self.successful_transactions / self.plan_transactions
        else:
            return 0

    @property
    def concurrent_per_process(self):
        """
        每个进程需要启动的并发链接数
        :return:
        """
        return int(self.concurrent / self.process_count)


@click.command()
@click.option('--concurrent', '-c', type=int, default=10, help='CONCURRENT users, default is 10')
@click.option('--reps', '-r', type=int, default=10, help='REPS, number of times to run the test.')
@click.option('--url', '-u', default='127.0.0.1:7777', help='URL, like 127.0.0.1:7777, ws://127.0.0.1:8000/echo')
@click.option('--msg_cmd', '-m', default=1, type=int, help='REMOTE_CMD, 1')
@click.option('--socket_type', '-t', default='socket', help='SOCKET_TYPE, socket/websocket')
@click.option('--process_count', '-p', default=1, help='process_count, 1')
def main(concurrent, reps, url, msg_cmd, socket_type, process_count):
    flood = Flood(concurrent, reps, url, msg_cmd, socket_type, process_count)
    flood.run()
    click.secho('done', fg='green')
    click.secho('Transactions:              %-10d hits' % flood.transactions)
    click.secho('Availability:              %-10.02f %%' % (flood.availability * 100))
    click.secho('Elapsed time:              %-10.02f secs' % flood.elapsed_time)
    click.secho('Response time:             %-10.02f secs' % flood.response_time)
    click.secho('Transaction rate:          %-10.02f trans/sec' % flood.transaction_rate)
    click.secho('Successful transactions:   %-10d hits' % flood.successful_transactions)
    click.secho('Failed transactions:       %-10d hits' % flood.failed_transactions)


if __name__ == '__main__':
    main()
