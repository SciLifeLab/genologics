import os
import sys
import warnings
from genologics.lims import Lims
from sys import version_info

if version_info.major == 2:
    import ConfigParser
    pyvers = 2
else:
    from configparser import ConfigParser
    pyvers = 3



'''
If config file is in a default location
Usage:
from genologics.config import BASEURI, USERNAME, PASSWORD

To use config from alternative location
Usage:
from genologics import start_lims

lims = start_lims(path_to_config)

# you won't need this once you have your lims object, but here they are:
BASEURI = lims.baseuri
PASSWORD = lims.password
USERNAME = lims.username
'''

spec_config = None

def get_config_info(config_file):
    if pyvers==2:
        config = ConfigParser.SafeConfigParser()
    else:
        config = ConfigParser()

    config.readfp(open(config_file))

    BASEURI = config.get('genologics', 'BASEURI').rstrip()
    USERNAME = config.get('genologics', 'USERNAME').rstrip()
    PASSWORD = config.get('genologics', 'PASSWORD').rstrip()

    if config.has_section('genologics') and config.has_option('genologics','VERSION'):
        VERSION = config.get('genologics', 'VERSION').rstrip()
    else:
        VERSION = 'v2'
    if config.has_section('logging') and config.has_option('logging','MAIN_LOG'):
        MAIN_LOG = config.get('logging', 'MAIN_LOG').rstrip()
    else:
        MAIN_LOG = None
    return BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG


def load_config(specified_config = None, startup=True):
    config_file = None
    if specified_config is not None:
        config_file = specified_config
    else:
        if pyvers == 2:
            config = ConfigParser.SafeConfigParser()
        else:
            config = ConfigParser()
        try:
            conf_file = config.read([os.path.expanduser('~/.genologicsrc'), '.genologicsrc',
                        'genologics.conf', 'genologics.cfg', '/etc/genologics.conf'])

            # First config file found wins
            config_file = conf_file[0]

        except:
            if not startup:
                warnings.warn("config file not specified or found in the expected locations.  Please provide create your own Genologics configuration file and provide a config path or place it in a default location (i.e: ~/.genologicsrc) as stated in README.md")
                sys.exit(-1)

    if startup and config_file is None:
        return warnings.warn("Config File Not Found"), None, None, None, None

    BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG = get_config_info(config_file)

    return BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG


def start_lims(config=None):
    '''start genologics lims object

    Args:
        config (str): path to genologics configuration file
    Returns:
        lims class object
    '''
    BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG = load_config(config, startup=False)
    lims = Lims(BASEURI, USERNAME, PASSWORD, VERSION)
    #lims.check_version()
    return lims


BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG = load_config(specified_config = spec_config, startup=True)
