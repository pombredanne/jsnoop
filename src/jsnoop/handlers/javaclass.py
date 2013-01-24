import struct
from os.path import join
from jsnoop.handlers.file import AbstractFile

class ClassFile(AbstractFile):
	def __init__(self, filepath, fileobj=None, parent_path=''):
		if not fileobj:
			path = join(parent_path, filepath)
			fileobj = open(path, 'rb')
		fileobj.seek(0)
		# Skip java compiler version.
		self.magic = read_magic(fileobj)
		self.version = read_version(fileobj)
		AbstractFile.__init__(self, filepath, fileobj, parent_path)

	@property
	def inmemory(self):
		return True

	def info(self):
		"""Returns the information related to this file, this includes those
		provided by jsnoop.common.file.AbstractFile.info() and info extracted
		from the binary class file."""
		fileinfo = AbstractFile.info(self)
		fileinfo['magic'] = self.magic
		fileinfo['version-string'] = major_version(self.version[0])
		fileinfo['version'] = self.version
		return fileinfo

"""
Source : https://github.com/victims/victims-hash
File : src/victims_hash/archive/reader/javaclass.py
@author: Grant C Murphy (gcmurphy)
"""
def read_magic(f):
	fmt = ">4B"
	buf = f.read(struct.calcsize(fmt))
	cafebabe = list(struct.unpack(fmt, buf))
	# assert(cafebabe == [ 0xca, 0xfe, 0xba, 0xbe ])
	return cafebabe

def major_version(ver):
	return {
		0x33 : "JSE7",
		0x32 : "JSE6",
		0x31 : "JSE5",
		0x30 : "JDK 1.4",
		0x2F : "JDK 1.3",
		0x2E : "JDK 1.2",
		0x2D : "JDK 1.1",
	}.get(ver, "Unkown")


def read_version(f):
	fmt = ">HH"
	buf = f.read(struct.calcsize(fmt))
	minor, major = struct.unpack(fmt, buf)
	return (major, minor)
