# 2013.05.22 09:50:14 UTC
#Embedded file name: /usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/mediabackends/helper.py
"""
Created on 06.05.2013

@author: matthias
"""
from twisted.python import failure
from twisted.internet import reactor, defer
import Queue
from threading import currentThread

def doBlockingCallFromMainThread(f, *a, **kw):
    """
      Modified version of twisted.internet.threads.blockingCallFromThread
      which waits 30s for results and otherwise assumes the system to be shut down.
      This is an ugly workaround for a twisted-internal deadlock.
      Please keep the look intact in case someone comes up with a way
      to reliably detect from the outside if twisted is currently shutting
      down.
    """
    queue = Queue.Queue()

    def _callFromThread():
        result = defer.maybeDeferred(f, *a, **kw)
        result.addBoth(queue.put)

    reactor.callFromThread(_callFromThread)
    result = None
    while True:
        try:
            result = queue.get(True, 30)
        except Queue.Empty as qe:
            if True:
                raise ValueError('Reactor no longer active, aborting.')
        else:
            break

    if isinstance(result, failure.Failure):
        result.raiseException()
    return result


def blockingCallFromMainThread(f, *a, **kw):
    if currentThread().getName() == 'MainThread':
        callMethod = lambda f, *a, **kw: f(*a, **kw)
    else:
        callMethod = doBlockingCallFromMainThread
    return callMethod(f, *a, **kw)


def callOnMainThread(func, *args, **kwargs):
    """
      Ensures that a method is being called on the main-thread.
      No return value here!
    """
    if currentThread().getName() == 'MainThread':
        reactor.callLater(0, func, *args, **kwargs)
    else:
        reactor.callFromThread(func, *args, **kwargs)