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

def unique_check(l,msg):
    "Check that l is of length 1, otherwise raise error, with msg appended"
    if len(l)==0:
        raise Exception("No item found for {0}".format(msg))
    elif len(l)!=1:
        raise Exception("Multiple items found for {0}".format(msg))

    
class EppLogger(object):
    """Logger class that collect stdout, stderr and info."""

    def __enter__(self):
        return self

    def __exit__(self,exc_type,exc_val,exc_tb):
        # If no exception has occured in block, turn off logging.
        if not exc_type:
            logging.shutdown()
            sys.stderr = self.saved_stderr
            sys.stdout = self.saved_stdout
        # Do not repress possible exception
        return False

    def __init__(self, log_file,level=logging.INFO):
        self.log_file = log_file
        self.level = level
        logging.basicConfig(
            level=self.level,
            format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
            filename=log_file,
            filemode='a'
            )

        stdout_logger = logging.getLogger('STDOUT')
        self.slo = self.StreamToLogger(stdout_logger, logging.INFO)
        self.saved_stdout = sys.stdout
        sys.stdout = self.slo

        stderr_logger = logging.getLogger('STDERR')
        self.sle = self.StreamToLogger(stderr_logger, logging.ERROR)
        self.saved_stderr = sys.stderr
        sys.stderr = self.sle

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
