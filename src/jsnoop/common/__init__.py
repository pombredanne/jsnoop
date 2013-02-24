from abc import abstractmethod, ABCMeta
from multiprocessing import Manager, Process
from multiprocessing.util import ForkAwareThreadLock
from multiprocessing.queues import Empty
from os import urandom

def enum(**enums):
	return type('Enum', (), enums)

class AbstractMPBorg(metaclass=ABCMeta):
	__mutex = ForkAwareThreadLock()
	__shared_state = {}
	def __init__(self, processes=4):
		self.__mutex.acquire()
		try:
			self.__dict__ = self.__shared_state
			if not self.is_initialized():
				self._initialize(processes)
				self.initialized = True
		finally:
			self.__mutex.release()

	def is_initialized(self):
		"""Tests if the shared state was initialized."""
		return self.__dict__.get('initialized', False)

	@abstractmethod
	def _initialize(self, processes):
		pass

SHUTDOWN_WAIT_TIMEOUT = 5

class AbstractQueueConsumer(AbstractMPBorg):
	def __init__(self, processes=4):
		AbstractMPBorg.__init__(self, processes=processes)

	@property
	def queue(self):
		return self._queue

	def _initialize(self, processes):
		"""Internal method to initialize all global variables. This initializes
		the manager, queue, pool and trigger the consumer."""
		self._terminator = 'TERMINATE'.encode() + urandom(10)
		self._manager = Manager()
		self._dispatch = self._manager.Pool(processes)
		self._queue = self._manager.Queue(-1)
		self._initialized = self._manager.Value(bool, False)
		# This is used to securely terminate the logging process once started
		self._process = Process(target=self._consumer)
		self._process.start()
		self._initialzied = True

	def shutdown(self):
		"""Kick starts the shut-down process for the Logging class"""
		self._dispatch.close()
		self._dispatch.join()
		self.queue.put(self._terminator)
		self._process.join(SHUTDOWN_WAIT_TIMEOUT)
		if self._process.is_alive():
			# We kill the process if it did not agree to die
			self._process.terminate()
			if not self.queue.empty():
				msg = 'Killed log consumer with messages still in queue.'
				print(type(self), msg)

	@abstractmethod
	def _record_handler(self, *args):
		pass

	def _put(self, *args):
		record = tuple(args)
		self.queue.put(record)

	def _consumer(self):
		"""This functions creates a process that consumes log messages on the
		queue till the instance's terminate key is received. This functions does
		nothing	if called once the instance's 'initialized' flag is set.

		This is intended for internal use only.."""
		if self.is_initialized():
			return None
		terminate = False
		while not (terminate and self.queue.empty()):
			try:
				record = self.queue.get(True)
				if isinstance(record, bytes) and self._terminator == record:
					terminate = True
				else:
					self._record_handler(*record)
			except Empty as e:
				# We should not get this, but just in case.
				pass
