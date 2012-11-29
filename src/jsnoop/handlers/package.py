from os.path import splitext
from jsnoop.common.archives import is_archive, make
from jsnoop.handlers.file import File
from jsnoop.handlers.manifest import ManifestFile
from jsnoop.handlers.signature import SignatureFile

# TODO: Find a better home for the initial bites minus the Package class
handled_packages = ['.zip', '.gz', '.bz2', '.tar', '.jar', '.sar', '.war']
extra_files = ['.MF', '.RSA', '.DSA']

def known_type(filepath):
	"""Check if a given file type is known to us"""
	filetype = splitext(filepath)[-1]
	return filetype in handled_packages + extra_files

def can_handle(filepath):
	"""Check if the given file is an archive we can handle"""
	valid = known_type(filepath) and is_archive(filepath)
	return valid

def get_handler(filepath):
	"""Helper function to fetch the correct handler based on """
	filetype = splitext(filepath)[-1]
	if filetype == '.MF':
		return ManifestFile
	elif filetype in ['.RSA', '.DSA']:
		return SignatureFile
	else:
		return File

# TODO: This needs to be parallelized as it is mostly a CPU bound task 
class Package():
	def __init__(self, filepath, prefix='', parent=None, process_all_files=False):
		self.filepath = filepath
		self.process_all_files = process_all_files
		self.fileinfo = File(filepath, prefix).info()
		self.fileinfo['parent'] = parent
		self.children = [self.fileinfo]
		self.process()

	def process(self):
		print('Snooping Archive: %s' % self.filepath)
		self.archive = make(self.filepath)
		for info in self.archive.infolist():
			# Decide if we are processing this or not
			if not self.archive.is_file(info) or \
			not (known_type(info.filename) or self.process_all_files):
				continue
			extracted_path = self.archive.extract(info)
			if can_handle(extracted_path):
				pkg = Package(extracted_path, self.archive.tempdir, self.fileinfo['sha512'])
				self.children += pkg.children
			else:
				handler = get_handler(extracted_path)
				fileinfo = handler(extracted_path, self.archive.tempdir).info()
				fileinfo['parent'] = self.fileinfo['sha512']
				self.children.append(fileinfo)
