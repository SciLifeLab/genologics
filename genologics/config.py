import ConfigParser, os

config = ConfigParser.SafeConfigParser()
conf_file = config.read([os.path.expanduser('~/.genologicsrc'), '.genologicsrc',
			'genologics.conf', 'genologics.cfg', '/etc/genologics.conf'])

# First config file found wins
config.readfp(open(conf_file[0]))

BASEURI = config.get('genologics', 'BASEURI').rstrip()
USERNAME = config.get('genologics', 'USERNAME').rstrip()
PASSWORD = config.get('genologics', 'PASSWORD').rstrip()
