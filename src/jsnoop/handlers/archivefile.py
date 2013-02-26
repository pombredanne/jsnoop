from jsnoop.handlers import AbstractFile
from pyrus.archives import is_archive, make_archive_obj

class ArchiveFile(AbstractFile):
	def __init__(self, filepath, fileobj=None, parent_path='',
				parent_sha512=None):
		arg = fileobj if fileobj else filepath
		if not is_archive(arg):
			# Oops, this was not really an archive
			raise ValueError
		AbstractFile.__init__(self, filepath, fileobj, parent_path,
							parent_sha512)
		self.archive = make_archive_obj(filepath, fileobj, True)

	@property
	def inmemory(self):
		return True

	def get_contents(self):
		"""Returns a list of info objects from the archive.
		"""
		return self.archive.infolist()

	def get_file_obj(self, member):
		"""Extracts a file from the archive and returns the corresponding
		file-like-object. If the member is a directory/link the archives module
		returns an empty BytesIO object.
		"""
		return self.archive.extract(member, True)

	def get_child_objects(self):
		children = []
		for child in self.get_contents():
			fileobj = self.get_file_obj(child)
			filename = self.archive.filename_from_info(child)
			path = self.filepath
			sha512 = self.checksums['sha512']
			children.append(ArchiveChild(filename, fileobj, path, sha512))
		return children

class ArchiveChild():
	def __init__(self, filename, fileobj, parent_path, parent_sha512):
		self.filename = filename
		self.fileobj = fileobj
		self.parent_path = parent_path
		self.parent_sha512 = parent_sha512
