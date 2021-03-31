import os
import sys
import warnings

try:
    from configparser import SafeConfigParser
except ImportError:
    from configparser import SafeConfigParser



'''
Usage:
from genologics.config import BASEURI, USERNAME, PASSWORD

Alternate Usage: 
from genologics import config
BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG = config.load_config(specified_config = <path to config file>) 
'''

spec_config = None

def get_config_info(config_file):
    config = SafeConfigParser()
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
        

def load_config(specified_config = None):
    if specified_config != None:
        config_file = specified_config
    else:
        config = SafeConfigParser()
        try:
            conf_file = config.read([os.path.expanduser('~/.genologicsrc'), '.genologicsrc',
                        'genologics.conf', 'genologics.cfg', '/etc/genologics.conf'])

            # First config file found wins
            config_file = conf_file[0]

        except:
            return None, None, None, None, None

    BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG = get_config_info(config_file)

    return BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG   
    

BASEURI, USERNAME, PASSWORD, VERSION, MAIN_LOG = load_config(specified_config = spec_config)
