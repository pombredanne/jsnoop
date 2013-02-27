from jsnoop.plugins import maven
from pyrus.mplogging import Logger, DEBUG

logger = Logger('test_maven', DEBUG)
maven.logger.set_log_level(DEBUG)

def check_poms(artifact):
	logger.debug('Testing local repo pom check')
	local = maven.MavenFileSystemRepos('local', maven.DEFAULT_LOCAL_URI)
	local.download_pom(artifact)
	logger.debug('Testing remote repo pom check')
	remote = maven.MavenHttpRemoteRepos('public', maven.DEFAULT_REMOTE_URI)
	remote.download_pom(artifact)

def test():
	artifact = maven.Artifact('ant', 'ant', '1.5')
	try:
		logger.debug('Testing artifact name generation')
		assert artifact.__str__() == 'ant:ant:1.5'
		logger.debug('Testing artifact path generation')
		assert artifact.to_maven_name('jar') == 'ant/ant/1.5/ant-1.5.jar'
	except:
		print('Artifact test failed')
	# Watch logs
	check_poms(artifact)

if __name__ == '__main__':
	test()
