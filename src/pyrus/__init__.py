from abc import abstractmethod, ABCMeta
from multiprocessing import Manager, Process
from multiprocessing.util import ForkAwareThreadLock
from multiprocessing.queues import Empty
from os import urandom
from time import sleep

def enum(**enums):
	return type('Enum', (), enums)

class AbstractMPBorg(metaclass=ABCMeta):
	_mutex = ForkAwareThreadLock()
	def __init__(self, *args, **kwds):
		self._mutex.acquire()
		try:
			if not hasattr(type(self), '_shared_state'):
				type(self)._shared_state = {}
			self.__dict__ = self._shared_state
			if not self.is_initialized():
				self._manager = Manager()
				self._initialize(*args, **kwds)
				self.initialized = self._manager.Value(bool, True)
		finally:
			self._mutex.release()

	def is_initialized(self):
		"""Tests if the shared state was initialized."""
		return self.__dict__.get('initialized', False)

	@abstractmethod
	def _initialize(self, *args, **kwds):
		pass

SHUTDOWN_WAIT_TIMEOUT = 5
QUEUE_GRACE_PERIOD = 0.1

class AbstractQueueConsumer(AbstractMPBorg):
	def __init__(self, consumers, *args, **kwds):
		AbstractMPBorg.__init__(self, consumers, *args, **kwds)

	@property
	def queue(self):
		return self._queue

	def _initialize(self, consumers):
		"""Internal method to initialize all global variables. This initializes
		the manager, queue, pool and trigger the consumer.

		If additional initializations need to be done, implentor can overwrite
		this method. Note that this should be called after additional
		initializations are performed."""
		self._terminator = 'TERMINATE'.encode() + urandom(10)
		self._queue = self._manager.Queue(-1)
		self._consumers = consumers
		self._start_consumers(consumers)

	def shutdown(self, timeout=SHUTDOWN_WAIT_TIMEOUT):
		"""Kick starts the shut-down process for the class"""
		self._stop_consumers(timeout)
		if self._process.is_alive():
			# We kill the process if it did not agree to die
			self._process.terminate()
			if not self.queue.empty():
				msg = 'Killed log consumer with messages still in queue.'
				print(type(self), msg)

	@abstractmethod
	def _record_handler(self, *args):
		"""Performs the desired action on the record received."""
		pass

	def _put(self, *args):
		record = tuple(args)
		self.queue.put(record)

	def _start_consumers(self, consumers):
		"""Starts the requested number of consumers

		The last consumer is marked as the 'sucker', this is the only consumer
		that will wait for queue to be empty after the terminate message is
		received.
		"""
		for i in range(consumers - 1):
			p = Process(target=self._consumer, args=(i,))
			p.start()
		self._process = Process(target=self._consumer,
							args=(consumers - 1, True))
		self._process.start()

	def _stop_consumers(self, timeout):
		"""Stops all consumers by sending as many terminate messages as there
		are consumers.

		This method waits till the original process that initiated the consumers
		finish."""
		for _ in range(self._consumers):
			self.queue.put(self._terminator)
		self._process.join(timeout)

	def _consumer(self, cid, sucker=False):
		"""Starts consuming from this instance's queue.

		This functions does nothing	if called once the instance's 'initialized'
		flag is already set.

		The will block till a new record is received from the queue. If the new
		record is this instance's terminate key, the function breaks when
		sucker=False. If sucker is True, the function will wait till all records
		are consumed."""
		if self.is_initialized():
			return None
		terminate = False
		while not ((terminate and sucker and self.queue.empty()) \
				or (terminate and not sucker)):
			self._mutex.acquire()
			try:
				record = self.queue.get(True)
			except Empty as _:
				# We should not get this, but just in case.
				pass
			finally:
				self._mutex.release()
			if isinstance(record, bytes) and self._terminator == record:
				terminate = True
				# Allow a grace period
				if sucker:
					sleep(QUEUE_GRACE_PERIOD)
			else:
				self._record_handler(*record)
