from jsnoop.handlers import AbstractFile

class SimpleFile(AbstractFile):
	def __init__(self, filepath, fileobj=None, parent_path='',
				parent_sha512=None):
		AbstractFile.__init__(self, filepath, fileobj, parent_path,
							parent_sha512)

	@property
	def inmemory(self):
		return True
