from jsnoop.handlers.archivefile import ArchiveFile
from jsnoop.handlers import get_handler_obj

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
