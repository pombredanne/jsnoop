import atexit
from multiprocessing import Manager
from io import BytesIO
from os.path import exists
from urllib.request import urlopen, Request

DOWNLOAD_USER_AGENT = 'python'
BUF_SIZE = 4096

# Download states
class DownloadException(Exception): pass
class DownloadStarted(object): pass
class DownloadDone(object): pass

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
	__shared_state = {'init':False}
	def __init__(self, processes=4):
		self.__dict__ = self.__shared_state
		if not self.init:
			self.__manager = Manager()
			self.__workers = self.__manager.Pool(processes)
			self.__downloads = self.__manager.dict()

	def __get_state(self, url):
		"""Returns the state of a given url.

		If a given url is in the downloads dictionary, it's state is returned
		and if it cannot be found a None object is returned.

		Expected states are DownloadStarted, DownloadDone and DownloadException.
		"""
		return self.__downloads.get(url, None)

	def is_done(self, url):
		"""Tests if the given url is known to be in DownloadDone state"""
		state = self.__get_state(url)
		return isinstance(state, DownloadDone)

	def is_error(self, url):
		"""Tests if the given url is known to be in DownloadException state"""
		state = self.__get_state(url)
		return isinstance(state, DownloadException)

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
			downloads_dict[url] = DownloadStarted()
			bio = download_bytes(url)
			dest.write(bio.getvalue())
			if dest != target:
				dest.close()
			downloads_dict[url] = DownloadDone()
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
		if url in self.__downloads and overwrite:
				del self.__downloads[url]
		result = self.__workers.apply_async(_DownloadPool._download,
									(url, target, self.__downloads, overwrite))
		if not async:
			result.wait()
			return self.__get_state(url)
		else:
			return result

	def _shutdown(self):
		"""Triggers the shutdown of download manager pool. Will wailt till
		all active pool workers finish downloads."""
		self.__workers.close()
		self.__workers.join()
		self.init = False

__download_pool = _DownloadPool()

def download(url, target, async=True, overwrite=False):
	"""Download a url to the given target.

	Keyword arguments:
	url -- the source url to be downloaded
	target -- the filepath/IO to write the received bytes to
	async -- do we wait for the download to complete? (default True)
	overwrite -- do we overwrite existing files? (default False)
	"""
	return __download_pool.download(url, target, async, overwrite)

@atexit.register
def __close_active_pools():
	"""Triggers shutdown on exit"""
	__download_pool._shutdown()
