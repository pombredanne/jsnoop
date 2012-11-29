from os.path import sep, exists, isfile, splitext, basename, dirname
from jsnoop.common.checksum import hexdigest

required_checksums = ['md5', 'sha1', 'sha256', 'sha512']

class File():
	def __init__(self, filepath, parent_path=''):
		assert exists(filepath)
		assert isfile(filepath)
		self.filepath = filepath
		self.path = dirname(filepath.replace(parent_path, '').lstrip(sep))
		self.name = basename(filepath)
		self.type = splitext(filepath)[-1].lower()
		self.prepare_checksums(filepath)

	def prepare_checksums(self, filepath):
		self.checksums = {}
		for algorithm in required_checksums:
			self.checksums[algorithm] = hexdigest(filepath, algorithm)

	def info(self):
		fileinfo = {}
		fileinfo['path'] = self.path
		fileinfo['name'] = self.name
		fileinfo['type'] = self.type
		for key in self.checksums:
			fileinfo[key] = self.checksums[key]
		return fileinfo
