from unittest import TestCase, main
from jsnoop.plugins import maven
from pyrus.mplogging import Logger, DEBUG, INFO

class TestMavenPlugin(TestCase):
	def setUp(self):
		maven.logger.set_log_level(DEBUG)
		self.remote = maven.MavenHttpRemoteRepos('public',
												maven.DEFAULT_REMOTE_URI)
		self.local = maven.MavenFileSystemRepos('public',
												maven.DEFAULT_LOCAL_URI)
		self.artifact = maven.Artifact('ant', 'ant', '1.5')
		self.artifact_sha1 = 'dcab88fc2a043c2479a6de676a2f8179e9ea2167'
		self.artifact_md5 = '902a360ecad98a34b59863c1e65bcf71'

	def test_artifact_name(self):
		self.assertEqual(self.artifact.__str__(), 'ant:ant:1.5')

	def test_artifact_path(self):
		self.assertEqual(self.artifact.maven_name(), 'ant/ant/1.5/ant-1.5.jar')

	def test_md5_remote(self):
		md5 = self.remote.fetch_checksum(self.artifact, 'md5')
		self.assertEqual(md5, self.artifact_md5)

	def test_sha1_remote(self):
		sha1 = self.remote.fetch_checksum(self.artifact, 'sha1')
		self.assertEqual(sha1, self.artifact_sha1)

	def test_sha1_local(self):
		sha1 = self.local.fetch_checksum(self.artifact, 'sha1')
		self.assertIn(sha1, [self.artifact_sha1, None])

	def tearDown(self):
		TestCase.tearDown(self)
		maven.logger.set_log_level(INFO)

if __name__ == '__main__':
	main()
