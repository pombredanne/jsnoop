from jsnoop.handlers import AbstractFile

class SimpleFile(AbstractFile):
	def __init__(self, filepath, fileobj=None, parent_path=''):
		AbstractFile.__init__(self, filepath, fileobj, parent_path)

	@property
	def inmemory(self):
		return True
