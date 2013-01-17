from subprocess import check_output, CalledProcessError
from jsnoop.handlers.file import AbstractFile

handled_signers = ['.rsa', '.dsa']

def decode_signer(filepath):
	"""Decodes the signer from the file at filepath"""
	# TODO: Figure out a pythonic way of doing this efficiently and to handle
	# inmemory stuff
	try:
		cmd = 'openssl pkcs7 -inform DER -in ' + filepath + ' -noout -print_certs -text'
		return check_output(cmd, shell=True)
	except CalledProcessError:
		# TODO: This is a hack we need a better way of dealing with this
		cmd = 'openssl x509 -in ' + filepath + ' -noout -text'
		return check_output(cmd, shell=True)

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
