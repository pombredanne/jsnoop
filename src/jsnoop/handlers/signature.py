from subprocess import check_output, CalledProcessError
from jsnoop.handlers.file import File

handled_signers = ['.rsa', '.dsa']

def decode_signer(filepath):
	"""Decodes the signer from the file at filepath"""
	#TODO: Figure out a pythonic way of doing this efficiently
	try:
		cmd = 'openssl pkcs7 -inform DER -in ' + filepath + ' -noout -print_certs -text'
		return check_output(cmd, shell=True)
	except CalledProcessError:
		#TODO: This is a hack we need a better way of dealing with this
		cmd = 'openssl x509 -in ' + filepath + ' -noout -text'
		return check_output(cmd, shell=True)

class SignatureFile(File):
	def __init__(self, filepath, parent_path=''):
		File.__init__(self, filepath)
		assert self.type in handled_signers
		self.signature = decode_signer(filepath)

	def info(self):
		fileinfo = File.info(self)
		fileinfo['signature'] = self.signature
		return fileinfo
