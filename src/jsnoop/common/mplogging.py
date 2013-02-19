import atexit
import time
from os import urandom
from logging import NOTSET, INFO, DEBUG, WARN, CRITICAL, addLevelName, getLevelName
from multiprocessing import Process, Pool, Manager, current_process
from multiprocessing.queues import Empty

SHUTDOWN_WAIT_TIMEOUT = 5

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

class Logging():
	"""Logging class is a multiprocessing safe logging class. This class is
	designed with the Borg DP in mind . (All instances of this class shares the
	same states.) An instance of this class is to be used to get loggers.

	By design, this acts like a server consuming messages from a MP Queue. The
	loggers received from get_logger() methed can communicate using this Queue.
	"""
	__manager = Manager()
	__shared_state = {
		'_Logging__terminator'	: 'TERMINATE'.encode() + urandom(10),
		'_Logging__manager'	: __manager,
		'_Logging__dispatch'	: Pool(processes=4),
		'_Logging__queue'	: __manager.Queue(-1),
		'_Logging__initialized'	: __manager.Value(bool, False),
		'_Logging__level'	: __manager.Value(int, INFO)
	}
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
		# This is used to securely terminate the logging process once started
		self.__process = Process(target=self.__consumer)
		self.__process.start()
		self.level = INFO
		self.__initialzied = True

	def __log_direct(self, name, level, message):
		log = str(LogMessage(name, level, message))
		print(log)

	def shutdown(self):
		"""Kick starts the shut-down process for the Logging class"""
		self.__dispatch.close()
		self.__dispatch.join()
		self.queue.put(self.__terminator)
		self.__process.join(SHUTDOWN_WAIT_TIMEOUT)
		if self.__process.is_alive():
			# We kill the process if it did not agree to die
			self.__process.terminate()
			if not self.queue.empty():
				msg = 'Killed log consumer with messages still in queue.'
				self.__log_direct(__name__, WARN, msg)

	def __consumer(self):
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
				if isinstance(record, bytes) and self.__terminator == record:
					terminate = True
				else:
					print(record)
			except Empty as e:
				# We should not get this, but just in case.
				pass

	def _log(self, msg):
		print('disp: ', self.__dispatch)
		self.__dispatch.apply_async(self.queue.put, (msg,))

# The global instance of Logging to kickstart log consumer on import
mplogging = Logging()

class Logger():
	"""A poor man's implementation of a Logger class for the use in
	Logging.get_logger()."""
	def __init__(self, name, level):
		self.level = level
		self.name = name

	def __log(self, level, msg):
		if level >= self.level:
			log = str(LogMessage(self.name, level, msg))
			mplogging._log(log)

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

def get_logger(name=__name__, level=None):
	"""Returns a Logger instance for the given name. If no level is given
	the global level is used. The class state caches the loggeres that are
	created and reuses them as required."""
	if level is None:
		level = mplogging.level
	return Logger(name, level)

@atexit.register
def __graceful_shutdown():
	"""This method triggers the shutdown of the logging consumer. This is
	triggerred only when the python interpreter exits."""
	get_logger(__name__).info('Shutting down logging')
	mplogging.shutdown()
