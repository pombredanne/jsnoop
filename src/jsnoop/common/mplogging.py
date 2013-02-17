import atexit
import time
from logging import NOTSET, INFO, DEBUG, WARN, CRITICAL, addLevelName, getLevelName
from multiprocessing import Process, Pool, Manager, current_process
from multiprocessing.queues import Empty

SHUTDOWN_WAIT_TIMEOUT = 5

class KillMessage():
	pass

class LogMessage():
	def __init__(self, name, level, msg):
		self.logtime = time.localtime()
		self.level = level
		self.msg = msg
		self.name = name
		self.pid = current_process().pid

	def __str__(self):
		level = getLevelName(self.level)
		return '[%s] [%s] [%s] [%s] %s' % (time.asctime(self.logtime), level,
						self.name, self.pid, self.msg)

class Logger():
	"""A poor man's implementation of a Logger class for the use in
	Logging.get_logger()."""
	def __init__(self, name, level, workers, queue):
		self.level = level
		self.name = name
		self.workers = workers
		self.queue = queue

	def __log(self, level, msg):
		if level <= self.level:
			log = LogMessage(self.name, level, msg)
			self.workers.apply_async(self.queue.put, (log,))

	def critical(self, msg):
		self.__log(CRITICAL, msg)

	def info(self, msg):
		self.__log(INFO, msg)

	def warning(self, msg):
		self.__log(WARN, msg)

	def debug(self, msg):
		self.__log(DEBUG, msg)

	def log(self, level, msg):
		self.__log(level, msg)


class Logging():
	"""Logging class is a multiprocessing safe logging class. This class is
	designed with the Borg DP in mind . (All instances of this class shares the
	same states.) An instance of this class is to be used to get loggers.

	By design, this acts like a server consuming messages from a MP Queue. The
	loggers received from get_logger() methed can communicate using this Queue.
	"""
	__shared_state = {}
	def __init__(self):
		self.__dict__ = self.__shared_state
		if not self.is_initialized():
			self.__initialize()

	def is_initialized(self):
		"""Tests if the shared state was initialized."""
		return self.__dict__.get('initialized', False)

	@property
	def queue(self):
		return self.__queue

	@property
	def level(self):
		try:
			return self.__level
		except:
			return NOTSET

	@level.setter
	def level(self, level):
		self.__level = level

	def addLevelName(self, level, levelName):
		"""Method adds a new level with a given name. This is just a wrapper for
		logging.addLevelName."""
		addLevelName(level, levelName)

	def __initialize(self):
		"""Internal method to initialize all global variables. This initializes
		the manager, queue, pool and trigger the consumer."""
		self.__manager = Manager()
		self.__dispatch = Pool(processes=4)
		self.__queue = self.__manager.Queue(-1)
		self.__process = Process(target=self.__consumer)
		self.__process.start()
		self.__active_loggers = {}
		self.level = NOTSET
		self.initialized = True

	def shutdown(self):
		"""Kick starts the shut-down process for the Logging class"""
		self.__dispatch.close()
		self.__dispatch.join()
		self.queue.put(KillMessage())
		self.__process.join(SHUTDOWN_WAIT_TIMEOUT)
		if self.__process.is_alive():
			# We kill the process if it did not agree to die
			self.__process.terminate()
			if not self.queue.empty():
				msg = 'Killed log consumer with messages still in queue.'
				warning = LogMessage(__name__, WARN, msg)
				print(warning)

	def __consumer(self):
		"""This functions creates a process that consumes log messages on the
		queue untile a None object is received. This functions does nothing
		if called once the instance's 'initialized' flag is set.

		This is intended for internal use only.."""
		if self.is_initialized():
			return None
		terminate = False
		while not (terminate and self.queue.empty()):
			try:
				record = self.queue.get(True)
				if isinstance(record, KillMessage):
					terminate = True
				elif isinstance(record, LogMessage):
					print(str(record))
				else:
					warning = LogMessage(__name__, WARN, "Object of type %s \
						found in logging queue" % (type(record)))
					print(str(warning))
			except Empty as e:
				# We should not get this, but just in case.
				pass

	def get_logger(self, name=__name__, level=None):
		"""Returns a Logger instance for the given name. If no level is given
		the global level is used. The class state caches the loggeres that are
		created and reuses them as required."""
		if level is None:
			level = self.level
		if name not in self.__active_loggers:
			self.__active_loggers[name] = Logger(name, level, self.__dispatch,
								self.queue)
		return self.__active_loggers[name]

# The global instance of Logging to kickstart log consumer on import
mplogging = Logging()

@atexit.register
def __graceful_shutdown():
	"""This method triggers the shutdown of the logging consumer. This is
	triggerred only when the python interpreter exits."""
	logger = mplogging.get_logger()
	logger.info('Shutting down multiprocessor logging')
	mplogging.shutdown()
