import subprocess
import os
import tarfile
import zipfile
from re import search, compile
from tempfile import mkdtemp
from abc import ABCMeta, abstractmethod
from genericpath import isdir
from io import BytesIO

native_support_os = ['posix']

def bytes_to_bio(filebytes):
	"""Creates a file like BytesIO object from given filebytes."""
	assert type(filebytes) is bytes
	return BytesIO(filebytes)

def fileobj_to_bio(fileobj):
	"""Creates a file like BytesIO object from given file object."""
	bio = BytesIO(fileobj.read())
	# Leave things as it were, seek to 0
	fileobj.seek(0)
	return bio

def file_to_bio(filepath):
	"""Creates a file like BytesIO object from given file on disk. We retrun an
	empty BytesIO object if the filepath points to a directory or a link.
	"""
	assert(os.path.exists(filepath))
	if os.path.isfile(filepath):
		return fileobj_to_bio(open(filepath, 'rb'))
	else:
		return BytesIO()

class AbstractArchive(metaclass=ABCMeta):
	def __init__(self, filepath, inmemory_processing=True,
				allow_unsafe_extraction=False):
		self.allow_unsafe_extraction = allow_unsafe_extraction
		self.filepath = filepath
		self.filelist = self.generate_filelist()
		self.check_unsafe()
		self.tempdir = None
		self.inmemory = inmemory_processing

	@property
	def tempdir(self):
		"""Gets the current value of the tempdir property."""
		try:
			return self.__tempdir
		except:
			return None

	@tempdir.setter
	def tempdir(self, value):
		"""Sets the tempdir location, we expect the directory path to exist. If
		a previous value existed we remove that directory."""
		try:
			if value != self.__tempdir:
				self.__cleanup()
		except:
			# Oops cleanup failed, might as well continue.
			# TODO: Better clean up?
			pass
		assert value is None or isdir(value)
		self.__tempdir = value

	@tempdir.deleter
	def tempdir(self):
		"""Deletes the tempdir property after proper clean up is performed
		usign the instance's cleanup() method."""
		self.__cleanup()
		del self.__tempdir

	@property
	def inmemory(self):
		"""Gets the inmemory property"""
		return self.__inmemory

	@inmemory.setter
	def inmemory(self, value):
		"""Sets the inmemory property. If we are processing inmemory we make
		sure all temporary directory stuff is removed and cleaned up, if we are
		not we create a new temp directory"""
		self.tempdir = None if value else mkdtemp(prefix="jsnoop_")
		self.__inmemory = value

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

	def __cleanup(self):
		"""Cleans up all files in the tempdir and sets the tempdir property
		to None. All further calls to tempdir will raise an AssertionError."""
		if self.tempdir is not None:
			# We import here to avoid the risk of python cleaning up rmtree
			# before an instance of this class is deleted. (__del__)
			from shutil import rmtree
			rmtree(self.tempdir)
			self.tempdir = None


	def __del__(self):
		# Clean up after yourself.
		self.__cleanup()

	@staticmethod
	def is_native():
		return False

	@abstractmethod
	def generate_filelist(self):
		"""Returns a list of filename_from_info strings"""
		return NotImplementedError

	@abstractmethod
	def extract(self, member, force_file_obj):
		"""Extracts a member (identified by filename_from_info) from the archive
		and returns its absolute path if inmemory and force_file_obj
		are False else returns a file-like object."""
		return NotImplemented

	@abstractmethod
	def extract_all(self, force_file_obj):
		"""Extracts all files in the archive and returns a dictionary mapping
		member.filename to absolute path on disk (if inmemory and force_file_obj
		are False) or file-like object (if inmemory is True or force_file_obj is
		True).
		"""
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
	def __init__(self, filepath, fileobj=None, inmemory_processing=True,
				allow_unsafe_extraction=False):
		# The ZipFile constructor cannot handle file objects other than
		# BytesIO for some reason. So enforcing it.
		if fileobj and not isinstance(fileobj, BytesIO):
			fileobj = fileobj_to_bio(fileobj)
		arg = fileobj if fileobj else filepath
		assert zipfile.is_zipfile(arg)
		self.archive = zipfile.ZipFile(arg)
		if fileobj:
			fileobj.seek(0)
		AbstractArchive.__init__(self, filepath, inmemory_processing,
								allow_unsafe_extraction)

	def generate_filelist(self):
		return self.archive.namelist()

	def infolist(self):
		return self.archive.infolist()

	def extract(self, member, force_file_obj=False):
		"""Extract a given member (ZipInfo Object or Filename).
		If inmemory mode is enabled, or if force_file_obj is set to True, we
		return file-like object derrived from the bytes returned by
		ZipFile.read() method (Converted using	archives.bytes_to_io method).

		Else if inmemory mode is disabled and force_file_obj is False, we return
		the the path of the extracted file on disk.
		"""
		if self.inmemory:
			# We use custom BytesIO obj as the zipfile.ZipExtFile cannot be
			# trusted to work with zipfile.ZipFile()
			# zipfile.ZipExtFile also has issues when the ZipFile was opened
			# using a file-like object.
			return bytes_to_bio(self.archive.read(member))
		else:
			filepath = self.archive.extract(member, self.tempdir)
			return file_to_bio(filepath) if force_file_obj else filepath

	def extract_all(self, force_file_obj=False):
		"""Performs extaction of all files in the current Zip Archive.
		If inmemory mode is enabled, or if force_file_obj is set to True, we
		return a dictionary where key is the filename and value is a file-like
		object returned by extract() method.

		Else if inmemory mode is disabled and force_file_obj is False,, we
		return a dict with the member name as key and the extracted location of
		the file on disk as value.
		"""
		files = {}
		if self.inmemory:
			for member in self.infolist():
				files[member.filename] = self.extract(member)
		else:
			self.archive.extractall(self.tempdir)
			for member in self.infolist():
				filepath = os.path.join(self.tempdir, member.filename)
				value = file_to_bio(filepath) if force_file_obj else filepath
				files[member.filename] = value
		return files

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
	def __init__(self, filepath, fileobj=None, inmemory_processing=True,
				allow_unsafe_extraction=False):
		# Risky business, we do not check if this is a valid tarfile
		# we watch it fail and burn. We do this as we have no reliable check
		# handling both bytes/name case liek in zipfile.
		if fileobj:
			self.archive = tarfile.TarFile(fileobj=fileobj)
		else:
			self.archive = tarfile.TarFile(name=filepath)
		AbstractArchive.__init__(self, filepath, inmemory_processing,
								allow_unsafe_extraction)

	def generate_filelist(self):
		return self.archive.getnames()

	def extract(self, member, force_file_obj=False):
		"""Extract a given member (TarInfo Object or Filename).
		If inmemory mode is enabled, or if force_file_obj is set to True, we
		return file-like object derrived from the bytes returned by
		TarFile.extractfile() method.

		Else if inmemory mode is disabled and force_file_obj is False, we return
		the the path of the extracted file on disk.

		Warning: If using force_file_obj=False, trying to extract a directory
		or a link will throw an assertion error.
		"""
		if self.inmemory:
			return self.archive.extractfile(member)
		else:
			self.archive.extract(member, self.tempdir)
			filepath = member.name if type(member) is tarfile.TarInfo else member
			filepath = os.path.join(self.tempdir, filepath)
			return file_to_bio(filepath) if force_file_obj else filepath

	def extract_all(self, force_file_obj=False):
		"""Performs extaction of all files in the current Zip Archive.
		If inmemory mode is enabled, or if force_file_obj is set to True, we
		return a dictionary where key is the filename and value is a file-like
		object returned by extract() method.

		Else if inmemory mode is disabled and force_file_obj is False,, we
		return a dict with the member name as key and the extracted location of
		the file on disk as value.
		"""
		files = {}
		if self.inmemory:
			for member in self.infolist():
				files[member.filename] = self.extract(member)
		else:
			self.archive.extractall(self.tempdir)
			for member in self.filelist:
				filepath = os.path.join(self.tempdir, member.filename)
				value = file_to_bio(filepath) if force_file_obj else filepath
				files[member.filename] = value
		return files

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
	def __init__(self, filepath, fileobj=None, inmemory_processing=False,
				allow_unsafe_extraction=False):
		# Native archives cannot support inmemory mode
		self.inmemory_processing = False
		self.path = filepath
		if fileobj:
			temp_path = os.path.join(mkdtemp(prefix='nativetar-'), filepath)
			os.makedirs(os.path.dirname(temp_path))
			with open(temp_path, 'wb') as f:
				f.write(fileobj.read())
				fileobj.seek(0)
			self.path = temp_path
		assert os.name in native_support_os
		AbstractArchive.__init__(self, filepath, inmemory_processing,
								allow_unsafe_extraction)

	def __del__(self):
		from shutil import rmtree
		path = self.path.replace(self.filepath)
		if os.path.exists(path):
			rmtree(path)

	@property
	def extract_cmd(self):
		return ['tar', '-C', self.tempdir, '-xf', self.path]

	def prepare_info(self):
		"""This method prepares additional information including file
		permissions, link information etc for later use. Here we make use of
		the output provided by the command tar -tvf. The additional information
		is stored in __infolist as NativeInfo objects"""
		# We expect the format:
		# permissions owner/group size date time filename_from_info
		regex = compile('([dlrwx-]*) [ ]*([a-zA-Z0-9/]*) [ ]*([0-9]*) ' +
					'[ ]*([0-9-]*) [ ]*([0-9:]*) [ ]*(.*)')
		cmd = ['tar', '-tvf', self.path]
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
		cmd = ['tar', '-tf', self.path]
		files = subprocess.check_output(cmd)
		return [ f.strip() for f in files.decode().strip().split('\n') ]

	def extract(self, member=None, force_file_obj=False):
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
			if not member:
				values = []
				for filename in self.filelist:
					filepath = os.path.join(path, filename)
					value = file_to_bio(filepath) if force_file_obj else filepath
					values.append(value)
				return values
			return path
		except subprocess.CalledProcessError:
			return None

	def extract_all(self, force_file_obj=False):
		return self.extract(None, force_file_obj)

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

def make_archive_obj(filepath, fileobj=None, inmemory_processing=True, allow_unsafe_extraction=False):
	"""This method allows for smart opening of an archive file. Currently this
	method can handle tar and zip archives. For the tar files, if the python
	library has issues, the file is attempted to be processed by using the
	tar command. (Note: the native classes are implemented to work only on
	posix machines)"""
	if not fileobj:
		assert os.path.isfile(filepath)
		test_arg = filepath
	else:
		test_arg = fileobj
	obj = None
	if zipfile.is_zipfile(test_arg):
		obj = ZipFile(filepath, fileobj, inmemory_processing,
					allow_unsafe_extraction)
	elif is_tarfile(test_arg):
		try:
			obj = TarFile(filepath, fileobj, inmemory_processing,
					allow_unsafe_extraction)
		except:
			obj = NativeTarFile(filepath, fileobj, inmemory_processing,
								allow_unsafe_extraction)
	else:
		raise Exception("Unknown Archive Type: " +
					"You should really just give me something I can digest!")
	return obj

def is_tarfile(arg):
	"""Helper function to test if a given filepath/file-like-object is of a
	tar like file.

	Limitation: We use name extension to determine this if the arg is a
	file-like-object. Valid extions are 'tar', 'gz', 'bz', 'bz2'."""
	if isinstance(arg, str):
		# Process filepaths
		tarfile.is_tarfile(arg)
	elif hasattr(arg, 'name'):
		# At the moment, we cannot check bytestreams for being tar files
		return os.path.splitext(arg.name)[-1] in ['tar', 'gz', 'bz', 'bz2']
	return False

def is_archive(arg):
	"""Helper function to test if a given filepath/file-like-object is of a
	an archive type we can handle."""
	last_position = arg.tell() if hasattr(arg, 'tell') else 0
	result = zipfile.is_zipfile(arg) or is_tarfile(arg)
	if not isinstance(arg, str):
		# Safety first since we handle file objects
		arg.seek(last_position)
	return result

