import hashlib

algorithms = {
	'md5' 	: hashlib.md5,
	'sha1'	: hashlib.sha1,
	'sha256': hashlib.sha256,
	'sha512': hashlib.sha512
	}

def hexdigest(arg, algorithm='sha512'):
	algorithm = algorithm.lower()
	assert algorithm in algorithms
	try:
		# Try to open the file and hash it
		with open(arg, mode='rb') as f:
			digest = algorithms[algorithm]()
			for buff in iter(f.read, b''):
				digest.update(buff)
	except IOError:
		# If the file could not be opened, hash the string arg
		digest = algorithms[algorithm](arg.encode())
	return digest.hexdigest()
