import subprocess
import os
import tarfile
import zipfile
from re import search, compile
from tempfile import mkdtemp
from abc import ABCMeta, abstractmethod

native_support_os = ['posix']

# TODO: Add inmemory extraction and manipulation support
class AbstractArchive(metaclass=ABCMeta):
	def __init__(self, filepath, tempdir, allow_unsafe_extraction):
		assert os.path.isdir(tempdir)
		self.__tempdir = tempdir
		self.allow_unsafe_extraction = allow_unsafe_extraction
		self.filepath = filepath
		self.filelist = self.generate_filelist()
		self.check_unsafe()

	@property
	def tempdir(self):
		assert self.__tempdir is not None
		return self.__tempdir

	def members(self):
		"""Returns a list of filenames strings from the archive"""
		return self.filelist

	def check_unsafe(self):
		"""If unsafe extractions are not allowed we check filenames in the 
		archives to see if any start with '/' or '..'. This identifies absolute
		and relative paths"""
		if not self.allow_unsafe_extraction:
			for filename in self.filelist:
				if filename.startswith(os.path.sep) or \
					filename.startswith('..'):
					raise Exception("Unsafe filename_from_info in archive %s" % \
								self.filepath)

	def cleanup(self):
		"""Cleans up all files in the tempdir and sets the tempdir property
		to None. All further calls to tempdir will raise an AssertionError."""
		# We import here to avoid the risk of python cleaning up rmtree
		# before an instance of this class is deleted. (__del__)
		from shutil import rmtree
		rmtree(self.tempdir)
		self.__tempdir = None

	def __del__(self):
		# Clean up after yourself.
		self.cleanup()

	@staticmethod
	def is_native():
		return False

	@abstractmethod
	def generate_filelist(self):
		"""Returns a list of filename_from_info strings"""
		return NotImplementedError

	@abstractmethod
	def extract(self, member):
		"""Extracts a member (identified by filename_from_info) from the archive and 
		returns its absolute path"""
		return NotImplemented

	@abstractmethod
	def extract_all(self):
		"""Extracts all files in the archive and returns the absolute path
		of the temporary directory"""
		return NotImplemented

	@abstractmethod
	def infolist(self):
		"""Returns a list of Info objects (TarInfo,ZipInfo) of all files
		in the archive."""
		return NotImplementedError

	@staticmethod
	def is_link(info):
		"""Checks if the given info object is that of a link"""
		return info.issym()

	@staticmethod
	def is_dir(info):
		"""Checks if the given info object is that of a directory"""
		return info.isdir()

	@classmethod
	def is_file(cls, info):
		"""Checks if the given info object is that of a regular file"""
		return not(cls.is_dir(info) or cls.is_link(info))

	@staticmethod
	def filename_from_info(info):
		"""Gives the filename stored in this info object"""
		return info.filename

class ZipFile(AbstractArchive):
	def __init__(self, filepath, tempdir, allow_unsafe_extraction=False):
		assert zipfile.is_zipfile(filepath)
		self.archive = zipfile.ZipFile(filepath)
		AbstractArchive.__init__(self, filepath, tempdir,
								allow_unsafe_extraction)

	def generate_filelist(self):
		return self.archive.namelist()

	def infolist(self):
		return self.archive.infolist()

	def extract(self, member):
		return self.archive.extract(member, self.tempdir)

	def extract_all(self):
		self.archive.extractall(self.tempdir)
		return self.tempdir

	@staticmethod
	def is_link(info):
		"""This method overrides the implementation in the abstract class 
		@AbstractArchive as the @zipfile.ZipInfo object does not have a issym()
		method."""
		assert type(info) is zipfile.ZipInfo
		# We use a hack to figure out if an info object a link
		# http://www.mail-archive.com/python-list@python.org/msg34223.html
		zip_link_attrs = ['0xa1ff0000', '0xa1ed0000']
		return hex(info.external_attr) in zip_link_attrs

	@staticmethod
	def is_dir(info):
		"""This method overrides the implementation in the abstract class 
		@AbstractArchive as the @zipfile.ZipInfo object does not have a isdir()
		method."""
		assert type(info) is zipfile.ZipInfo
		return info.filename.endswith('/')


class TarFile(AbstractArchive):
	def __init__(self, filepath, tempdir, allow_unsafe_extraction=False):
		assert tarfile.is_tarfile(filepath)
		self.archive = tarfile.TarFile(filepath)
		AbstractArchive.__init__(self, filepath, tempdir,
								allow_unsafe_extraction)

	def generate_filelist(self):
		return self.archive.getnames()

	def extract(self, member):
		self.archive.extract(member, self.tempdir)
		filepath = member.name if type(member) is tarfile.TarInfo else member
		return os.path.join(self.tempdir, filepath)

	def extract_all(self):
		self.archive.extractall(self.tempdir)
		return self.tempdir

	def infolist(self):
		return self.archive.getmembers()

	@staticmethod
	def filename_from_info(info):
		return info.name


class AbstractNativeArchive(AbstractArchive):
	@staticmethod
	def is_native():
		return True

class NativeTarFile(AbstractNativeArchive):
	def __init__(self, filepath, tempdir, allow_unsafe_extraction=False):
		assert os.name in native_support_os
		AbstractArchive.__init__(self, filepath, tempdir,
								allow_unsafe_extraction)

	@property
	def extract_cmd(self):
		return ['tar', '-C', self.tempdir, '-xf', self.filepath]

	def prepare_info(self):
		"""This method prepares additional information including file 
		permissions, link information etc for later use. Here we make use of 
		the output provided by the command tar -tvf. The additional information
		is stored in __infolist as NativeInfo objects"""
		# We expect the format:
		# permissions owner/group size date time filename_from_info
		regex = compile('([dlrwx-]*) [ ]*([a-zA-Z0-9/]*) [ ]*([0-9]*) ' +
					'[ ]*([0-9-]*) [ ]*([0-9:]*) [ ]*(.*)')
		cmd = ['tar', '-tvf', self.filepath]
		output = subprocess.check_output(cmd)
		self.__infolist = []
		filelist = []
		for line in output.decode().strip().split('\n'):
			match = search(regex, line)
			if match:
				filename = match.group(6).strip()
				linkto = None
				if filename.find('->') >= 0:
					filename, linkto = [ i.strip()
									for i in filename.split('->')]
				permissions = match.group(1)
				owner, group = match.group(2).split('/')
				filesize = int(match.group(3))
				self.__infolist.append(NativeInfo(filename, permissions,
												owner, group, filesize, linkto))
				filelist.append(filename)
		return filelist

	def generate_filelist(self):
		return self.prepare_info()

	def generate_simple_filelist(self):
		cmd = ['tar', '-tf', self.filepath]
		files = subprocess.check_output(cmd)
		return [ f.strip() for f in files.decode().strip().split('\n') ]

	def extract(self, member=None):
		cmd = self.extract_cmd
		path = self.tempdir
		if member:
			if type(member) is NativeInfo:
				filename = member.filename_from_info
			else:
				filename = member
			assert filename in self.filelist
			cmd.append(filename)
			path = os.path.join(path, filename)
		try:
			subprocess.call(cmd)
			return path
		except subprocess.CalledProcessError:
			return None

	def extract_all(self):
		return self.extract()

	def infolist(self):
		return self.__infolist

class NativeInfo():
	def __init__(self, filename, permissions, owner, group, filesize, linkto=None):
		self.filename_from_info = filename
		self.permissions = permissions
		self.owner = owner
		self.group = group
		self.filesize = filesize
		self.linkto = linkto

	def issym(self):
		return self.permissions.startswith('l')

	def isdir(self):
		return self.permissions.startswith('d')

def make(filepath, allow_unsafe_extraction=False):
	"""This method allows for smart opening of an archive file. Currently this
	method can handle tar and zip archives. For the tar files, if the python
	library has issues, the file is attempted to be processed by using the 
	tar command. (Note: the native classes are implemented to work only on
	posix machines)"""
	assert os.path.isfile(filepath)
	tempdir = mkdtemp()
	obj = None
	if zipfile.is_zipfile(filepath):
		obj = ZipFile(filepath, tempdir, allow_unsafe_extraction)
	elif tarfile.is_tarfile(filepath):
		try:
			obj = TarFile(filepath, tempdir, allow_unsafe_extraction)
		except:
			obj = NativeTarFile(filepath, tempdir, allow_unsafe_extraction)
	else:
		raise Exception("Unknown Archive Type: " +
					"You should really just give me something I can digest!")
	return obj

def is_archive(filepath):
	return (zipfile.is_zipfile(filepath) or tarfile.is_tarfile(filepath))
