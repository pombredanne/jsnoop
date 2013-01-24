from subprocess import getstatusoutput
from jsnoop.handlers.file import AbstractFile

handled_signers = ['.rsa', '.dsa']

def decode_signer(filepath):
	"""Decodes the signer from the file at filepath"""
	# TODO: Figure out a pythonic way of doing this efficiently and to handle
	# inmemory stuff
	commands = [
			'openssl pkcs7 -inform DER -in %s -noout -print_certs -text',
			'openssl x509 -in %s -noout -text'
			]
	for cmd in commands:
		(status, output) = getstatusoutput(cmd % (filepath))
		if status == 0:
			break
	return output

class SignatureFile(AbstractFile):
	def __init__(self, filepath, fileobj=None, parent_path=''):
		AbstractFile.__init__(self, filepath, fileobj, parent_path)
		assert self.type in handled_signers
		self.signature = decode_signer(self.filepath)

	@property
	def inmemory(self):
		return False

	def info(self):
		fileinfo = AbstractFile.info(self)
		fileinfo['signature'] = self.signature
		return fileinfo
