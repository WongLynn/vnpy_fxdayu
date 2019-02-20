import logging
from enum import Enum
from copy import copy
from datetime import datetime
from functools import partial
from multiprocessing import Queue, Process
from multiprocessing.queues import Empty
from threading import Thread

from .RestClient import RestClient, Request, RequestStatus

class MpCommand(Enum):
    STOP = 0
    START = 1


def callback(qout, req_id, data, request):
    qout.put((req_id, data, request))

def onFailed(qout, req_id, httpStatusCode, request):
    qout.put((req_id, httpStatusCode, request))

def onError(qout, req_id, exceptionType, exceptionValue, tb, request):
    qout.put((req_id, exceptionType, exceptionValue, tb, request))


class PriorityRestClient(RestClient):
    def __init__(self, *args, **kwargs):
        super(PriorityRestClient, self).__init__(*args, **kwargs)
        self._priority = 0
        self._mp_qin = Queue()
        self._mp_qout = Queue()
        self._mp_req = {}
        self._mp_req_id = 0
        self._mp_worker = None
        self._mp_receiver = None

    @property
    def priority(self):
        return self._priority

    def set_priority(self, priority):
        self._priority = priority

    def start(self, n=3):
        """启动"""
        self._mp_worker = Process(target=self._run_mp_worker, args=(self._mp_qin, self._mp_qout, self.urlBase, n))
        self._mp_worker.daemon = True 
        self._mp_worker.start()
        self._mp_receiver = Thread(targe=self._run_mp_receiver)
        self._mp_receiver.start()
        super(PriorityRestClient, self).start(n=3)

    #----------------------------------------------------------------------
    def stop(self):
        """
        强制停止运行，未发出的请求都会被暂停（仍处于队列中）
        :return:
        """
        self._active = False
        self._mp_qin.put((0, MpCommand.STOP.value))
        
    #----------------------------------------------------------------------
    def join(self):
        self._queue.join()
        self._mp_worker.join()
        self._mp_receiver.join()

    def addRequest(self,
                   method,          # type: str
                   path,            # type: str
                   callback,        # type: Callable[[dict, Request], Any]
                   params=None,     # type: dict
                   data=None,       # type: dict
                   headers=None,    # type: dict
                   onFailed=None,   # type: Callable[[int, Request], Any]
                   onError=None,    # type: Callable[[type, Exception, traceback, Request], Any]
                   extra=None,       # type: Any
                   priority=None,
                   ):               # type: (...)->Request ):
        if priority <= 0:
            return super().addRequest(method, path, callback, params=params, 
                data=data, headers=headers, onFailed=onFailed, onError=onError)
        else:                
            request = Request(method, path, params, data, headers, callback)
            request.createDatetime = datetime.now()
            request.deliverDatetime = None
            request.responseDatetime = None
            mr = copy(request)
            mr.callback = None
            request.extra = extra
            request.onFailed = onFailed
            request.onError = onError
            self._mp_req_id += 1
            self._queue.put((self._mp_req_id, mr))

    @staticmethod
    def _run_mp_worker(self, qin, qout, url, n):
        client = RestClient()
        client.init(url)
        client.start(n)
        while True:
            try:
                req_id, req, *args = self._mp_qin.get(timeout=1)
                if req_id == 0:
                    if MpCommand(req) == MpCommand.STOP:
                        logging.debug("exit restclient multiprocess worker")
                        break
                else:
                    self.addRequest(
                        req.method,
                        req.path,
                        callback=partial(callback, qout, req_id),
                        params=req.params,
                        data=req.data,
                        headers=req.headers,
                        onFailed=partial(onFailed, qout, req_id),
                        onError=partial(onError, qout, req_id),
                        extra=req.extra,
                    )
            except Empty:
                pass
            except Exception as e:
                logging.exception(e)

    def _run_mp_receiver(self):
        while self._active:
            try:
                req_id, *args = self._mp_qout.get(timeout=1)
            except Empty:
                continue
            try:
                req = self._mp_req.pop(req_id)  
            except KeyError:
                logging.error("lost info of rest request [%s]", req_id)
                continue
            try:
                *_, request = args
                if request.deliverDatatime:
                    req.deliverDatetime = request.deliverDatetime
                    self._queueing_times.append((req.deliverDatetime - req.createDatetime).total_seconds())
                if request.responseDatetime:
                    req.responseDatetime = request.responseDatetime
                    self._response_times.append((req.responseDatetime - req.deliverDatetime).total_seconds())
                req.status = request.status
                if req.status == RequestStatus.success:
                    req.callback(*args)
                elif req.status == RequestStatus.failed:
                    if req.onFailed:
                        req.onFailed(*args)
                    else:
                        self.onFailed(*args)
                elif req.status == RequestStatus.error:
                    if req.onError:
                        req.onError(*args)
                    else:
                        self.onError(*args)
            except Exception as e:
                req.status = RequestStatus.error
                t, v, tb = sys.exc_info()
                if req.onError:
                    req.onError(t, v, tb, request)
                else:
                    self.onError(t, v, tb, request)
