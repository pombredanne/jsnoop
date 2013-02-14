from jsnoop.handlers import AbstractFile

class ManifestFile(AbstractFile):
	def __init__(self, filepath, fileobj=None, parent_path='',
				parent_sha512=None):
		AbstractFile.__init__(self, filepath, fileobj, parent_path,
							parent_sha512)
		self.manifestinfo = {}
		self.parse()

	@property
	def inmemory(self):
		return True

	def __appendinfo(self, header, value):
		self.manifestinfo[header] = value

	def parse(self):
		"""Parses the headers from the manifest file. Limited validation is
		performed. We parse assuming the manifest meets the specification."""
		if self.fileobj:
			manifest = self.fileobj
		else:
			manifest = open(self.filepath, 'r', encoding='utf8')
		header, value = None, None
		for line in manifest.readlines():
			if isinstance(line, bytes):
				line = line.decode()
			if line[0] == ' ':
				# if the leading line is a SPACE, we assume its part of the
				# previous header
				value += line.strip()
			elif header and line.strip() == '':
				# We have already got a header and we hit an empty line,
				# we assume we have reached the end of useful information
				self.__appendinfo(header, value)
				break
			else:
				if header:
					# If we hit this block we assume we completely parsed the
					# header.
					self.__appendinfo(header, value)
				first_colon = line.find(':')
				if first_colon >= 0:
					# If the line has a colon, we know it is not part of the
					# previous header value, so it must be the end of the
					# header name
					header = line[:first_colon].strip()
					value = line[first_colon + 1:].strip()

	def info(self):
		"""Returns the information related to this file, this includes those
		provided by jsnoop.common.file.AbstractFile.info() and the manifest headers."""
		fileinfo = AbstractFile.info(self)
		fileinfo['manifest-info'] = self.manifestinfo
		return fileinfo
