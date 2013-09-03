#!/usr/bin/env python
from nose.tools import assert_almost_equal, assert_equal, assert_true
from os.path import isdir,isfile
from os import listdir
import os
import sys

from genologics.epp import EppLogger
import logging

file_path = os.path.realpath(__file__)
test_dir_path = os.path.dirname(file_path)
tmp_dir_path = test_dir_path + '/nose_tmp_output'
CWD = os.getcwd()

class TestLog(object):
    def setUp(self):
        """Create temporary dir if necessary,
        otherwise clear contents of it"""
        if not isdir(tmp_dir_path):
            os.mkdir(tmp_dir_path)
        self.tearDown()
        os.chdir(test_dir_path)

    def tearDown(self):
        """remove temporary output files"""
        for d in os.listdir(tmp_dir_path):
            d_path = os.path.join(tmp_dir_path,d)
            try:
                os.remove(d_path)
            except:
                for f in os.listdir(d_path):
                    f_path = os.path.join(d_path,f)
                    os.remove(f_path)
                os.rmdir(d_path)

        assert os.listdir(tmp_dir_path) == []


    def test_stderr(self):
        """ Stderr should be printed to stderr and logged"""
        tmp_file = os.path.join(tmp_dir_path,'tmp_log')
        saved_stderr = sys.stderr
        tmp_stderr = os.path.join(tmp_dir_path,'tmp_stderr')
        with open(tmp_stderr,'w') as sys.stderr:
            with EppLogger(tmp_file, prepend=False) as epp_logger:
                print >> sys.stderr, 'stderr nosetest'
        sys.stderr = saved_stderr
        with open(tmp_stderr,'r') as stderr:
            stream_lines = stderr.readlines()
        assert_true('stderr nosetest' in stream_lines[-1])

        with open(tmp_file,'r') as log_file:
            log_lines = log_file.readlines()
        assert_true('stderr nosetest' in log_lines[-1])

    def test_stdout(self):
        """ Stdout should be logged but not printed"""
        tmp_file = os.path.join(tmp_dir_path,'tmp_log')
        saved_stdout = sys.stdout
        tmp_stdout = os.path.join(tmp_dir_path,'tmp_stdout')
        with open(tmp_stdout,'w') as sys.stdout:
            with EppLogger(tmp_file, prepend=False) as epp_logger:
                print >> sys.stdout, 'stdout nosetest'
        sys.stdout = saved_stdout
        with open(tmp_stdout,'r') as stdout:
            stream_lines = stdout.readlines()
        assert_true(not stream_lines)

        with open(tmp_file,'r') as log_file:
            log_lines = log_file.readlines()
        assert_true('stdout nosetest' in log_lines[-1])
        
    def test_exception(self):
        """ Exceptions should be printed and logged"""
        # Hard to test, if exceptions are caught in a try statement,
        # they will not be printed...
        pass
