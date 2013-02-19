import atexit
from multiprocessing import Pool, Manager
from io import BytesIO
from os.path import exists
from urllib.request import urlopen, Request

DOWNLOAD_USER_AGENT = 'python'
BUF_SIZE = 4096

class DownloadException(Exception): pass
class DownloadStarted(object): pass
class DownloadDone(object): pass

def download_bytes(url):
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
	bio = download_bytes(url)
	return bio.getvalue().decode()

class DownloadPool():
	__shared_state = {'init':False}
	def __init__(self, processes=4):
		self.__dict__ = self.__shared_state
		if not self.init:
			self.__manager = Manager()
			self.__workers = self.__manager.Pool(processes)
			self.__downloads = self.__manager.dict()

	def __get_state(self, url):
		return self.__downloads.get(url, None)

	def is_done(self, url):
		state = self.__get_state(url)
		return isinstance(state, DownloadDone)

	def is_error(self, url):
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

	def download(self, url, target, overwrite=False, async=True):
		if url in self.__downloads and overwrite:
				del self.__downloads[url]
		result = self.__workers.apply_async(DownloadPool._download,
									(url, target, self.__downloads, overwrite))
		if not async:
			result.wait()
			return self.__get_state(url)
		else:
			return result

	def _shutdown(self):
		self.__workers.close()
		self.__workers.join()
		self.init = False
		print('shutdown complete')

__download_pool = DownloadPool(4)

def download(url, target, overwrite=False, async=True):
	return __download_pool.download(url, target, overwrite, async)

@atexit.register
def __close_active_pools():
	__download_pool._shutdown()
