from os.path import splitext
from jsnoop.common.archives import is_archive, make
from jsnoop.handlers.file import File
from jsnoop.handlers.manifest import ManifestFile
from jsnoop.handlers.signature import SignatureFile
from jsnoop.handlers.javaclass import ClassFile

# TODO: Find a better home for the initial bites minus the Package class
handled_packages = ['.zip', '.gz', '.bz2', '.tar', '.jar', '.sar', '.war']
extra_files = ['.MF', '.RSA', '.DSA', '.class']

def known_type(filepath):
	"""Check if a given file type is known to us"""
	filetype = splitext(filepath)[-1]
	return filetype in handled_packages + extra_files

def can_handle(arg):
	"""Check if the given file is an archive we can handle"""
	return is_archive(arg)

def get_handler(filepath):
	"""Helper function to fetch the correct handler based on """
	filetype = splitext(filepath)[-1]
	if filetype == '.MF':
		return ManifestFile
	elif filetype in ['.RSA', '.DSA']:
		return SignatureFile
	elif filetype in ['.class']:
		return ClassFile
	else:
		return File

# TODO: This needs to be parallelized as it is mostly a CPU bound task
class Package():
	def __init__(self, filepath, fileobj=None, parent=None,
				process_all_files=False):
		self.filepath = filepath
		self.fileobj = fileobj
		self.process_all_files = process_all_files
		self.fileinfo = File(filepath, fileobj).info()
		self.fileinfo['parent'] = parent
		self.children = [self.fileinfo]
		self.process()

	def process(self):
		self.archive = make(self.filepath, self.fileobj, True)
		for info in self.archive.infolist():
			# Decide if we are processing this or not
			if not self.archive.is_file(info) or \
			not (known_type(info.filename) or self.process_all_files):
				continue
			fileobj = self.archive.extract(info)
			if can_handle(fileobj):
				pkg = Package(info.filename, fileobj, self.fileinfo['sha512'])
				self.children += pkg.children
			else:
				handler = get_handler(info.filename)
				fileinfo = handler(info.filename, fileobj).info()
				fileinfo['parent'] = self.fileinfo['sha512']
				self.children.append(fileinfo)
