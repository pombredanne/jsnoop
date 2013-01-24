from os import makedirs
from os.path import sep, exists, isfile, splitext, basename, join, dirname
from jsnoop.common.checksum import hexdigest
from abc import abstractproperty, ABCMeta
from tempfile import mkdtemp

required_checksums = ['md5', 'sha1', 'sha256', 'sha512']

class AbstractFile(metaclass=ABCMeta):
	def __init__(self, filepath, fileobj=None, parent_path=''):
		self.filepath = filepath
		self.fileobj = fileobj
		self.path = dirname(filepath.replace(parent_path, '').lstrip(sep))
		self.name = basename(filepath)
		self.type = splitext(filepath)[-1].lower()
		self.persist()
		# Use filebytes given, as this maybe in memory processing
		self.prepare_checksums()

	@abstractproperty
	def inmemory(self):
		return True

	@property
	def filepath(self):
		if self.__ondisk is None:
			return self.__filepath
		else:
			return self.__ondisk

	@filepath.setter
	def filepath(self, value):
		self.__filepath = value

	def persist(self):
		# We use a separate internal property to handle deletion when the
		# filepath is actually valid
		self.__ondisk = None
		if self.fileobj is not None and not self.inmemory:
			temp_dir = mkdtemp(prefix='jsnoop.file.persist.')
			temp_file = join(temp_dir, self.filepath)
			makedirs(dirname(temp_file))
			self.fileobj.seek(0)
			with open(temp_file, 'wb') as f:
				f.write(self.fileobj.read())
				self.fileobj.seek(0)
			self.__ondisk = temp_file

	def __del__(self):
		if self.__ondisk:
			from shutil import rmtree
			rmtree(self.__ondisk.replace(self.__filepath, ''))

	def prepare_checksums(self):
		if not self.fileobj:
			# If we are given a filepath make sure if its a valid file
			assert exists(self.filepath) and isfile(self.filepath)
			fileinput = self.filepath
		else:
			fileinput = self.fileobj
		self.checksums = {}
		for algorithm in required_checksums:
			self.checksums[algorithm] = hexdigest(fileinput, algorithm)

	def info(self):
		fileinfo = {}
		fileinfo['path'] = self.path
		fileinfo['name'] = self.name
		fileinfo['type'] = self.type
		for key in self.checksums:
			fileinfo[key] = self.checksums[key]
		return fileinfo

class File(AbstractFile):
	def __init__(self, filepath, fileobj=None, parent_path=''):
		AbstractFile.__init__(self, filepath, fileobj, parent_path)

	@property
	def inmemory(self):
		return True
