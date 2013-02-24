import atexit
from multiprocessing import Manager
from io import BytesIO
from os import getcwd
from os.path import exists, isdir, join
from urllib.request import urlopen, Request
from multiprocessing.util import ForkAwareThreadLock
from multiprocessing.managers import BaseManager
from jsnoop.common.mplogging import get_logger

logger = get_logger('jsnoop.common.download')

DOWNLOAD_USER_AGENT = 'python'
BUF_SIZE = 4096

# Download states
class DownloadState(object):
	def __init__(self, url):
		self.url = url

class DownloadException(Exception): pass

class DownloadStarted(DownloadState): pass

class DownloadDone(DownloadStarted):
	def __init__(self, url, memobj=None):
		DownloadStarted.__init__(self, url)
		self.memobj = memobj

def download_bytes(url):
	"""This is the workhorse method for the download module. This method
	takes a url and returns a BytesIO object of the content at the url. The read
	is done in chunks for BUF_SIZE."""
	bio = BytesIO()
	request = Request(url=url)
	request.add_header('User-Agent', DOWNLOAD_USER_AGENT)
	source = urlopen(request)
	while True:
		buf = source.read(BUF_SIZE)
		if not len(buf) > 0:
			break
		bio.write(buf)
	source.close()
	return bio

def download_string(url):
	"""A wrapper method to retreive/download string at a url. The returned value
	is the decoded string of the BytyesIO object received from download_bytes."""
	bio = download_bytes(url)
	return bio.getvalue().decode()

class _DownloadPool():
	"""A shared state class (Borg) acting as the download manager.
	This class blocks the interpreter's exit till all downloads are completed.
	"""
	__mutex = ForkAwareThreadLock()
	__shared_state = {'init':False}
	def __init__(self, processes=4):
		_DownloadPool.__mutex.acquire()
		try:
			self.__dict__ = self.__shared_state
			if not self.init:
				logger.debug('Starting Download Pool')
				self.__manager = Manager()
				self.__workers = self.__manager.Pool(processes)
				self.__downloads = self.__manager.dict()
				self.init = True
		finally:
			_DownloadPool.__mutex.release()

	def get_state(self, url):
		"""Returns the state of a given url.

		If a given url is in the downloads dictionary, it's state is returned
		and if it cannot be found a None object is returned.

		Expected states are DownloadStarted, DownloadDone and DownloadException.
		"""
		return self.__downloads.get(url, None)

	def is_done(self, url):
		"""Tests if the given url is known to be in DownloadDone state"""
		state = self.get_state(url)
		return isinstance(state, DownloadDone)

	def is_error(self, url):
		"""Tests if the given url is known to be in DownloadException state"""
		state = self.get_state(url)
		return isinstance(state, DownloadException)

	def discard_download(self, state):
		if isinstance(state, DownloadDone):
			url = state.url
			del self.__downloads[url]

	def get_download_result(self, url, discard=True):
		result = None
		if self.is_done(url):
			state = self.get_state(url)
			result = state.memobj
			self.discard(state)
		return result

	@classmethod
	def _download(cls, url, target, downloads_dict, overwrite=False):
		if url in downloads_dict:
			return
		try:
			assert not exists(target) or overwrite
			if not hasattr(target, 'write'):
				dest = open(target, 'wb')
			else:
				dest = target
			downloads_dict[url] = DownloadStarted(url)
			bio = download_bytes(url)
			dest.write(bio.getvalue())
			if dest != target:
				dest.close()
			downloads_dict[url] = DownloadDone(url, target)
		except Exception as e:
			print(e)
			downloads_dict[url] = DownloadException(url, e)

	def download(self, url, target, async=True, overwrite=False):
		"""Downloads the given url to the specified target.

		Warning: using buffers as targets could be problematic.

		Keyword arguments:
		url -- the source url to be downloaded
		target -- the filepath/IO to write the received bytes to
		async -- do we wait for the download to complete? (default True)
		overwrite -- do we overwrite existing files? (default False)
		"""
		logger.debug('Received %sdownlad request: %s' % (
												'async ' if async else '', url))
		if url in self.__downloads and overwrite:
				del self.__downloads[url]
		result = self.__workers.apply_async(_DownloadPool._download,
									(url, target, self.__downloads, overwrite))
		if not async:
			result.wait()
			return self.get_state(url)
		else:
			return result

	def shutdown(self):
		"""Triggers the shutdown of download manager pool. Will wailt till
		all active pool workers finish downloads."""
		logger.debug('Shutting down Download Pool')
		self.__workers.close()
		self.__workers.join()
		self.init = False

class DownloadManager(BaseManager): pass

DownloadManager.register('DownloadPool', _DownloadPool)
__download_manager = DownloadManager()
__download_manager.start()
__download_pool = __download_manager.DownloadPool()

def download(url, target=None, async=True, overwrite=False):
	"""Download a url to the given target.

	If a target is not provided, a new BytesIO object is created and used.

	Keyword arguments:
	url -- the source url to be downloaded
	target -- the filepath/IO to write the received bytes to
	async -- do we wait for the download to complete? (default True)
	overwrite -- do we overwrite existing files? (default False)
	"""
	if not target:
		target = BytesIO()
	return __download_pool.download(url, target, async, overwrite)

@atexit.register
def __close_active_pools():
	"""Triggers shutdown on exit"""
	__download_pool.shutdown()
