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
		# Try opening the file or assuming that arg is a file-like object
		f = open(arg, mode='rb') if isinstance(arg, str) else arg
		# If we get here, we have to remember where we started
		last_position = f.tell() if hasattr(f, 'tell') else 0
		digest = algorithms[algorithm]()
		for buff in iter(f.read, b''):
			digest.update(buff)
		if f is arg:
			# Assume that we processed a file-like object
			arg.seek(last_position)
		else:
			# If we opened a file, be nice and close it
			f.close()
	except (IOError, AttributeError):
		# If the file could not be opened, try convering the arg into bytes
		# then hash it
		inbytes = arg.encode() if type(arg) is str else arg
		# We can only process bytes
		assert type(inbytes) is bytes
		digest = algorithms[algorithm](arg.encode())
	return digest.hexdigest()
