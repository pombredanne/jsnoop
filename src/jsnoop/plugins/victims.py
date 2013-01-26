import json
import pickle
from urllib.request import urlopen
from datetime import datetime, MINYEAR
from os.path import isfile

VICTIMS_URI = 'http://localhost:5000'
TIMEOUT = 1
VICTIMS_CACHE = 'victims.cache'
DATE_FRMT = '%Y-%m-%dT%H:%M:%S'

def fetch_json(timestamp, server=VICTIMS_URI, is_removals=False):
	"""
	Retreives database entries using the victims REST-API and returns them as
	a list of dictionaries.
	"""
	data = []
	operation = 'remove' if is_removals else 'update'
	try:
		url = '%s/service/v2/%s/%s' % (VICTIMS_URI, operation, timestamp)
		req = urlopen(url, timeout=TIMEOUT)
		encoding = req.headers.get_content_charset()
		body = req.readall().decode(encoding)
		data = json.loads(body)
		data = [] if 'error' in data else data
	except:
		# TODO: Warning log?
		data = []
	return data

class LocalDatabase():
	"""
	Class for handling a local instance of the victims database. We store only
	those information we need.
	"""
	def __init__(self, server=VICTIMS_URI, cache=VICTIMS_CACHE, no_cache=False):
		timestamp = datetime(MINYEAR, 1, 1).strftime(
									'000' if MINYEAR == 1 else '' + DATE_FRMT)
		self.__db = {'updated': timestamp, 'entries': []}
		self.cache = None if no_cache else cache
		self.server = server
		self.__load()
		self.update()

	@property
	def entries(self):
		"""
		The etries property lists all the entries in the database. Each entry
		will be a dict where the key is the sha512 of the jar, and the value
		is a dict containtain the keys 'hash', 'cves', 'name', 'vendor',
		'version' and 'classes' (a list of sha512 sums).
		"""
		return self.__db['entries']

	@property
	def last_updated(self):
		"""
		Indicates when this database content was last updated.
		"""
		return self.__db['updated']

	def __load(self):
		if self.cache and isfile(self.cache):
			with open(self.cache, "rb") as f:
				self.__db = pickle.load(f)

	def __store(self):
		if self.cache:
			with open(self.cache, "wb") as f:
				pickle.dump(self.__db, f, pickle.HIGHEST_PROTOCOL)

	def update(self):
		"""
		Updates the database with changes from the server after the last_updated
		timestamp.
		"""
		timestamp = self.last_updated
		update_time = datetime.now().strftime(DATE_FRMT)
		updates = self.__parse_entries(fetch_json(timestamp, self.server))
		removals = self.__parse_entries(fetch_json(timestamp, self.server,
												True))
		if len(updates) > 0 or len(removals) > 0:
			# We need to process only if there are some changes
			self.__merge(updates, removals)
			self.__db['updated'] = update_time
			self.__store()

	def __parse_entry(self, entry):
		attrs = ['hash', 'cves', 'name', 'vendor', 'version']
		fields = entry['fields']
		parsed = { k:fields[k] for k in attrs }
		# For class based subset matching
		parsed['classes'] = list(fields['hashes']['sha512']['files'].values())
		return parsed

	def __parse_entries(self, entries):
		parsed = {}
		for entry in entries:
			entry = self.__parse_entry(entry)
			parsed[entry['hash']] = entry
		return parsed

	def __merge(self, updates={}, removals={}):
		new_entries = {}
		entries = self.__db['entries']
		# Process the updates first
		for key in updates:
			new_entries[key] = updates[key]
		# Add old entries that were not updated nor removed
		for key in entries:
			if key not in new_entries and key not in removals:
				new_entries[key] = entries[key]
		self.__db['entries'] = new_entries

	def match_archive(self, sha512):
		"""
		Gets a list of cves if the given hash matches any entry in the database.
		"""
		result = []
		if sha512 in self.entries:
			result = self.entries[sha512]['cves']
		return result

	def match_file_set(self, hashes):
		"""
		Gets a list of cves if the given list of hashes matches any
		complet set of classes for any entry in the database.
		"""
		# TODO: Implement when v2 is out
		return []
