import atexit
from io import BytesIO
from time import sleep
from os.path import exists
from urllib.request import urlopen, Request
from multiprocessing.managers import BaseManager
from jsnoop.common.mplogging import get_logger
from jsnoop.common import AbstractQueueConsumer

logger = get_logger('jsnoop.common.download')

DOWNLOAD_USER_AGENT = 'python'
BUF_SIZE = 4096

# Download states
class DownloadState(object):
	def __init__(self, url):
		self.url = url

class DownloadException(Exception): pass

class Downloading(DownloadState): pass

class Done(DownloadState):
	def __init__(self, url, memobj=None):
		DownloadState.__init__(self, url)
		self.memobj = memobj

class DownloadResult():
	def __init__(self, url):
		self.url = url

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

class DownloadPool(AbstractQueueConsumer):
	def __init__(self, consumers=4):
		AbstractQueueConsumer.__init__(self, consumers)

	def _initialize(self, consumers):
		self._downloads = self._manager.dict()
		self._results = self._manager.dict()
		AbstractQueueConsumer._initialize(self, consumers)

	def get_state(self, url):
		"""Returns the state of a given url.

		If a given url is in the downloads dictionary, it's state is returned
		and if it cannot be found a None object is returned.

		Expected states are DownloadStarted, DownloadDone and DownloadException.
		"""
		return self._downloads.get(url, None)

	def discard_result(self, result):
		assert isinstance(result, DownloadResult)
		if result.url in self._downloads:
			del self._downloads[result.url]

	def wait(self, result):
		while (result.url not in self._downloads):
			sleep(0.5)

	def fetch_download(self, result, block=False, discard_done=True):
		assert isinstance(result, DownloadResult)
		if block:
			self.wait(result)
		if result.url in self._downloads:
			state = self._downloads[result.url]
			if isinstance(state, Done):
				value = state.memobj
				if discard_done:
					self.discard_result(result)
				return value
		return None

	def _download(self, url, target, overwrite):
		if not target:
			target = BytesIO()
		if url in self._downloads:
			known_state = self.get_state(url)
			if known_state \
			and not isinstance(known_state, DownloadException) \
			and not overwrite:
				return
			else:
				self.discard_result(url)
		try:
			if isinstance(target, str):
				# Give taget is a string, we assume its a file path
				if exists(target) and not overwrite:
					return
				dest = open(target, 'wb')
			else:
				# If not a filepath, must be a stream right?
				dest = target
			self._downloads[url] = Downloading(url)
			bio = download_bytes(url)
			dest.write(bio.getvalue())
			if dest != target:
				dest.close()
			self._downloads[url] = Done(url, target)
		except Exception as e:
			self._downloads[url] = DownloadException(url, e)

	def _record_handler(self, url, target, overwrite):
		logger.debug('Downloading %s' % (url))
		self._download(url, target, overwrite)

	def download(self, url, target, async=True, overwrite=False):
		"""Downloads the given url to the specified target.

		Warning: using buffers as targets could be problematic.

		Keyword arguments:
		url -- the source url to be downloaded
		target -- the dest to write the received bytes (default BytesIO())
		async -- do we wait for the download to complete? (default True)
		overwrite -- do we overwrite existing files? (default False)
		"""
		result = DownloadResult(url)
		if not async:
			self._download(url, target, overwrite)
			self.wait(result)
		else:
			self._put(url, target, overwrite)
		return result

class DownloadManager(BaseManager): pass

DownloadManager.register('DownloadPool', DownloadPool)

__download_manager = DownloadManager()
__download_manager.start()
__download_pool = __download_manager.DownloadPool()

def download(url, target=None, async=True, overwrite=False):
	"""Download a url to the given target.

	If a target is not provided, a new BytesIO object is created and used.

	Keyword arguments:
	url -- the source url to be downloaded
	target -- the dest to write the received bytes (default BytesIO())
	async -- do we wait for the download to complete? (default True)
	overwrite -- do we overwrite existing files? (default False)
	"""
	return __download_pool.download(url, target, async, overwrite)

def fetch_result(result, block=True, discard_done=True):
	return __download_pool.fetch_download(result, block, discard_done)

def download_async(url, target=None, overwrite=False):
	return download(url, target, True, overwrite)

def download_blocking(url, target=None, overwrite=False):
	return download(url, target, False, overwrite)

@atexit.register
def __close_active_pools():
	"""Triggers shutdown on exit"""
	# We wait infinitely for downloads to finish
	__download_pool.shutdown(None)
