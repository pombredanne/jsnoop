#! /usr/bin/env python3

import sys
from os.path import basename, join, isfile, isdir
from os import listdir
from jsnoop.package import Package
from jsnoop.plugins.victims import LocalDatabase
from optparse import OptionParser
from multiprocessing import Pool
""" This is an example script that takes as input an archive file, snoops it
and writes the results to an output text file. No fancy stuff is done to the
output, all info is output as a string(dictionary)."""

output_ext = 'manifest'

def write_to_file(filepath, pkg):
	output_file = '%s.%s' % (basename(filepath), output_ext)
	with open(output_file, 'w') as output:
		for child in pkg.info:
			output.write(str(child) + '\n')
	print('Manifest written to %s' % output_file)

def scan_victims(pkg):
	print('Scaning for victims: %s' % (pkg.handler.info()['name']))
	vdb = LocalDatabase()
	for child in pkg.info:
		if child['type'] == '.jar':
			matches = vdb.match_archive(child['sha512'])
			if len(matches) > 0:
				cve_str = ','.join(matches)
				filename = join(child['path'], child['name'])
				print('Victim-Match : %s\n%s\n' % (cve_str,
                                        filename))

def _process(filepath, process_all_files):
	print('Snooping file: %s' % filepath)
	pkg = Package(filepath, process_all_files=process_all_files)
	scan_victims(pkg)
	write_to_file(filepath, pkg)

def process(files, process_all_files=False):
	pool = Pool(processes=4)
	for filepath in files:
		pool.apply_async(_process, (filepath, process_all_files))
	pool.close()
	pool.join()

def main():
	usage = 'usage: %prog [options] filename'
	parser = OptionParser(usage)
	parser.add_option('-d', '--dir', dest='directory',
					help='snoop all files in DIRECTORY')
	parser.add_option('-a', '--all-files', dest='allfiles',
					action='store_false', help='process all files in archive')
	(options, args) = parser.parse_args()
	files = []
	if len(args) < 1 and not options.directory:
		parser.error('No input specified.')
	if len(args) == 1:
		files.append(args[0])
	if options.directory:
		if not isdir(options.directory):
			parser.error('-d requires a valid directory')
		basedir = options.directory
		for path in listdir(basedir):
			path = join(basedir, path)
			if isfile(path):
				files.append(path)
				print('adding ', path)
	process(files, options.allfiles)

if __name__ == '__main__':
	main()
