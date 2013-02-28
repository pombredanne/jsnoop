from unittest import TestCase, main
from jsnoop.plugins import maven
from pyrus.mplogging import Logger, DEBUG, INFO

class TestMavenPlugin(TestCase):
	def setUp(self):
		maven.logger.set_log_level(DEBUG)
		self.remote = maven.MavenHttpRemoteRepos('public',
												maven.DEFAULT_REMOTE_URI)
		self.artifact = maven.Artifact('ant', 'ant', '1.5')

	def test_artifact_name(self):
		self.assertEqual(self.artifact.__str__(), 'ant:ant:1.5')

	def test_artifact_path(self):
		self.assertEqual(self.artifact.maven_name(), 'ant/ant/1.5/ant-1.5.jar')

	def test_sha1(self):
		expected = 'dcab88fc2a043c2479a6de676a2f8179e9ea2167'
		received = self.remote.fetch_checksum(self.artifact)
		self.assertEqual(received, expected)

	def test_md5(self):
		expected = '902a360ecad98a34b59863c1e65bcf71'
		received = self.remote.fetch_checksum(self.artifact, 'md5')
		self.assertEqual(received, expected)

	def tearDown(self):
		TestCase.tearDown(self)
		maven.logger.set_log_level(INFO)

if __name__ == '__main__':
	main()
