#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
	name='jsnoop',
	version='0.0.1',
	description='Java Archives and file snooping toolkit.',
	long_description='',
	author='Arun Babu Neelicattu',
	url="https://github.com/abn/jsnoop",
	download_url="https://github.com/abn/jsnoop",

	dependency_links=[
			'http://github.com/abn/pyrus/tarball/master#egg=pyrus-0.0.1'
			],

	install_requires=[
			'pyrus'
			],

	# license="",

	packages=find_packages('src', exclude=("pyrus",)),
	package_dir={'': 'src'},
	# exclude_package_data={ '': ['pyrus'] },
	include_package_data=True,

	# test_suite="",

	classifiers=[
		'Intended Audience :: Developers',
		'Intended Audience :: System Administrators',
		'Programming Language :: Python',
		'Topic :: Analysis',
		'Topic :: Software Development :: Libraries :: Python Modules',
	],
)
