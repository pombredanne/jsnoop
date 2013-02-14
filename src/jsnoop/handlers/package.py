from os.path import splitext
from jsnoop.common.archives import is_archive
from jsnoop.handlers.simplefile import SimpleFile
from jsnoop.handlers.manifest import ManifestFile
from jsnoop.handlers.signature import SignatureFile
from jsnoop.handlers.javaclass import ClassFile
from jsnoop.handlers.archivefile import ArchiveFile

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
		return SimpleFile

def get_handler_obj(filepath, fileobj=None, parent_path='', parent_sha512=None):
	# Try to process as an archive
	handler = None
	try:
		handler = ArchiveFile(filepath, fileobj, parent_path, parent_sha512)
	except ValueError:
		handler = get_handler(filepath)
		handler = handler(filepath, fileobj, parent_path, parent_sha512)
	return handler

# TODO: This needs to be parallelized as it is mostly a CPU bound task
class Package():
	def __init__(self, filepath, fileobj=None, parent_path='',
				parent_sha512=None, process_all_files=False):
		self.handler = get_handler_obj(filepath, fileobj, parent_path,
									parent_sha512)
		self.info = [self.handler.info()]
		self.process_all_files = process_all_files
		self.process()

	def process(self):
		if isinstance(self.handler, ArchiveFile):
			for child in self.handler.get_child_objects():
				pkg = Package(child.filename, child.fileobj, child.parent_path,
							child.parent_sha512)
				self.info += pkg.info



