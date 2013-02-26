import atexit
import time
from logging import NOTSET, INFO, DEBUG, WARN, CRITICAL, addLevelName, getLevelName
from multiprocessing import Process, current_process
from multiprocessing.managers import BaseManager, BaseProxy
from pyrus import AbstractQueueConsumer

DFAULT_LOG_LEVEL = INFO

class LogMessage():
	def __init__(self, name, level, msg, pid=None):
		self.logtime = time.localtime()
		self.level = level
		self.msg = msg
		self.name = name
		if pid:
			self.pid = pid
		else:
			self.pid = current_process().pid

	def __str__(self):
		level = getLevelName(self.level)
		return '[%s] [%s] [%s] [%s] %s' % (time.asctime(self.logtime), level,
						self.name, self.pid, self.msg)

class _Logging(AbstractQueueConsumer):
	"""_Logging class is a multiprocessing safe logging class. This class is
	designed with the Borg DP in mind . (All instances of this class shares the
	same states.) An instance of this class is to be used to get loggers.

	By design, this acts like a server consuming messages from a MP Queue. The
	loggers received from get_logger() methed can communicate using this Queue.
	"""
	def __init__(self, consumers=1):
		AbstractQueueConsumer.__init__(self, consumers)

	@property
	def level(self):
		try:
			return self.__level
		except:
			return NOTSET

	@level.setter
	def level(self, level):
		self.__level = level

	def get_log_level(self):
		return self.level

	def set_log_level(self, level):
		self.level = level

	def addLevelName(self, level, levelName):
		"""Method adds a new level with a given name. This is just a wrapper for
		logging.addLevelName."""
		addLevelName(level, levelName)

	def _initialize(self, consumers):
		"""Internal method to initialize all global variables. This initializes
		the manager, queue, pool and trigger the consumer."""
		self.level = DFAULT_LOG_LEVEL
		# This is used to securely terminate the logging process once started
		AbstractQueueConsumer._initialize(self, consumers)

	def __log_direct(self, name, level, message):
		log = str(LogMessage(name, level, message))
		print(log)

	def _record_handler(self, record):
		print(record)

	def log(self, name, level, msg, pid):
		log = str(LogMessage(name, level, msg, pid))
		self._put(log)

class _Logger():
	"""A poor man's implementation of a _Logger class for the use in
	_Logging.get_logger()."""
	def __init__(self, name, level, server, pid):
		self.level = level
		self.name = name
		self.server = server

	def _log(self, pid, level, msg):
		if level >= self.level:
			args = (self.name, level, msg, pid)
			p = Process(target=self.server.log, args=args)
			p.start()

	def get_log_level(self):
		return self.level

	def set_log_level(self, level):
		self.level = level

	def critical(self, pid, msg):
		self._log(pid, CRITICAL, msg)

	def info(self, pid, msg):
		self._log(pid, INFO, msg)

	def warning(self, pid, msg):
		self._log(pid, WARN, msg)

	def warn(self, pid, msg):
		self._log(pid, WARN, msg)

	def debug(self, pid, msg):
		self._log(pid, DEBUG, msg)

	def log(self, pid, level, msg):
		self._log(pid, level, msg)

class _LoggerProxy(BaseProxy):
	def __init__(self, token, serializer, manager=None,
		authkey=None, exposed=None, incref=True):
		BaseProxy.__init__(self, token, serializer, manager=manager, authkey=authkey, exposed=exposed, incref=incref)
		self.pid = current_process().pid

	# Generate normal proxy methods
	for meth in ['get_log_level', 'set_log_level']:
		exec('''def %s(self, *args, **kwds):
		return self._callmethod(%r, args, kwds)''' % (meth, meth))

	# Generate proxy methods that require current pid
	for meth in ['critical', 'log', 'info', 'warning', 'warn', 'debug']:
		exec('''def %s(self, *args, **kwds):
		pid = current_process().pid
		return self._callmethod(%r, (pid,) + args, kwds)''' % (meth, meth))

# A simple manager so we are multiprocessing safe
class LoggingManager(BaseManager): pass

# Register classes
LoggingManager.register('Logging', _Logging)
LoggingManager.register('Logger', _Logger, _LoggerProxy)

# Start the module logging manager
__logging_manager = LoggingManager()
__logging_manager.start()

# The global instance of _Logging to kickstart log consumer on import
__mplogging = __logging_manager.Logging()

def Logger(name=__name__, level=None):
	"""Returns a _Logger instance for the given name. If no level is given
	the global level is used. The class state caches the loggeres that are
	created and reuses them as required."""
	if level is None:
		level = __mplogging.get_log_level()
	pid = current_process().pid
	return __logging_manager.Logger(name, level, __mplogging, pid)

def set_log_level(level):
	"""Sets the global logging level"""
	__mplogging.set_log_level(level)

def get_log_level():
	"""Returns the global logging level"""
	return __mplogging.get_log_level()

@atexit.register
def __graceful_shutdown():
	"""This method triggers the shutdown of the logging consumer. This is
	triggerred only when the python interpreter exits."""
	Logger(__name__).debug('Shutting down logging')
	__mplogging.shutdown()
