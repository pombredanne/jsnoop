from abc import abstractmethod, ABCMeta
from multiprocessing.util import ForkAwareThreadLock

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
		raise NotImplemented
