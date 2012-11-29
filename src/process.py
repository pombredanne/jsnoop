#! /usr/bin/env python3

import sys
from os.path import exists, basename
from jsnoop.handlers.package import Package

""" This is an example script that takes as input an archive file, snoops it
and writes the results to an output text file. No fancy stuff is done to the 
output, all info is output as a string(dictionary)."""

output_ext = 'manifest'

def process(filepath, process_all_files=False):
	pkg = Package(filepath, process_all_files=process_all_files)
	output_file = '%s.%s' % (basename(filepath), output_ext)
	output = open(output_file, 'w')
	for child in pkg.children:
		output.write(str(child) + '\n')
	print('Manifest written to %s' % output_file)

if __name__ == '__main__':
	if not len(sys.argv) == 2:
		sys.exit('Usage: %s <Input File>' % sys.argv[0])
	filepath = sys.argv[1]
	if not exists(filepath):
		sys.exit('Invalid input file %s' % filepath)
	process(filepath)
