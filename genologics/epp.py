import logging
import sys
import os
from shutil import copy

def attach_file(src,resource):
    """Attach file at src to given resource

    Copies the file to the current directory, EPP node will upload this file
    automatically if the process output is properly set up"""
    original_name = os.path.basename(src)
    new_name = resource.id + '_' + original_name
    dir = os.getcwd()
    location = os.path.join(dir,new_name)
    print "Moving {0} to {1}".format(src,location)
    copy(src,location)


class StreamToLogger(object):
   """Fake file-like stream object that redirects writes to a logger instance.
   
   source: 
   http://www.electricmonk.nl/log/2011/08/14/
   redirect-stdout-and-stderr-to-a-logger-in-python/
   """
   def __init__(self, logger, log_level=logging.INFO):
      self.logger = logger
      self.log_level = log_level
      self.linebuf = ''
 
   def write(self, buf):
      for line in buf.rstrip().splitlines():
         self.logger.log(self.log_level, line.rstrip())
 

def configure_logging(log_file):
    """Set up logging so both stdout and stderr is logged to the log_file"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
        filename=log_file,
        filemode='a'
        )
    stdout_logger = logging.getLogger('STDOUT')
    sl = StreamToLogger(stdout_logger, logging.INFO)
    sys.stdout = sl
    
    stderr_logger = logging.getLogger('STDERR')
    sl = StreamToLogger(stderr_logger, logging.ERROR)
    sys.stderr = sl

def unique_check(l,msg):
    "Check that l is of length 1, otherwise raise error, with msg appended"
    if len(l)==0:
        raise Exception("No item found for {0}".format(msg))
    elif len(l)!=1:
        raise Exception("Multiple items found for {0}".format(msg))

