#! /usr/bin/env python3

import sys
from os.path import exists, basename, join
from jsnoop.package import Package
from jsnoop.plugins.victims import LocalDatabase
""" This is an example script that takes as input an archive file, snoops it
and writes the results to an output text file. No fancy stuff is done to the
output, all info is output as a string(dictionary)."""

output_ext = 'manifest'

def write_to_file(pkg):
	output_file = '%s.%s' % (basename(filepath), output_ext)
	with open(output_file, 'w') as output:
		for child in pkg.info:
			output.write(str(child) + '\n')
	print('Manifest written to %s' % output_file)

def scan_victims(pkg):
	print('Scaning for victims...')
	vdb = LocalDatabase()
	for child in pkg.info:
		if child['type'] == '.jar':
			matches = vdb.match_archive(child['sha512'])
			if len(matches) > 0:
				cve_str = ','.join(matches)
				filename = join(child['path'], child['name'])
				print('Victim-Match : %s\n%s\n' % (cve_str,
                                        filename))

def process(filepath, process_all_files=False):
	print('Snooping file...')
	pkg = Package(filepath, process_all_files=process_all_files)
	scan_victims(pkg)
	write_to_file(pkg)

if __name__ == '__main__':
	if not len(sys.argv) == 2:
		sys.exit('Usage: %s <Input File>' % sys.argv[0])
	filepath = sys.argv[1]
	if not exists(filepath):
		sys.exit('Invalid input file %s' % filepath)
	process(filepath)
