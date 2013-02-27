jsnoop
======

A simple tool to interrogate a given archive file for its contents and embedded jars. This allows you to generate a catalog of contents and programmatically analyse this information.

This project makes use of the the pyrus package. (https://github.com/abn/pyrus).

Setup/Start development environment
------
The following creates a dev environment under the directory jsnoop.dev. You can change the name of this directory by editing the script provided.

```bash
git clone git@github.com:abn/jsnoop.git
cd jsnoop
source scripts/start-dev-env.sh
```
Installation for use
-----
You can install this using _easy_install_ or _pip_
```bash
easy_install http://github.com/abn/jsnoop/tarball/master#egg=jsnoop-0.0.1
```

```bash
pip http://github.com/abn/jsnoop/tarball/master#egg=jsnoop-0.0.1
```
*NOTE:* This is not a stable module yet, so I suggest using a virtualenv.
