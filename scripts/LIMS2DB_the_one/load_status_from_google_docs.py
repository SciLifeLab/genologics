#!/usr/bin/env python
import sys
import os
import time
from  datetime  import  datetime
from uuid import uuid4
import hashlib
from optparse import OptionParser
import logging
import bcbio.google
import scilifelab.google.project_metadata as pmeta
import bcbio.pipeline.config_loader as cl
from bcbio.google import _to_unicode, spreadsheet
import couchdb


#           GOOGLE DOCS
def get_google_document(ssheet_title, wsheet_title, client):
    ssheet = bcbio.google.spreadsheet.get_spreadsheet(client, ssheet_title)
    wsheet = bcbio.google.spreadsheet.get_worksheet(client, ssheet, wsheet_title)
    content = bcbio.google.spreadsheet.get_cell_content(client,ssheet,wsheet)
    ss_key = bcbio.google.spreadsheet.get_key(ssheet)
    ws_key = bcbio.google.spreadsheet.get_key(wsheet)
    return content, ws_key, ss_key

def make_client(CREDENTIALS_FILE):
    credentials = bcbio.google.get_credentials({'gdocs_upload': {'gdocs_credentials': CREDENTIALS_FILE}})
    client = bcbio.google.spreadsheet.get_client(credentials)
    return client

def get_column(ssheet_content, header, col_cond=0):
    colindex=''
    for j, row in enumerate(ssheet_content):
        if colindex == '':
            for i, col in enumerate(row):
                if col_cond <= i and colindex == '':
                    if str(col).strip().replace('\n','').replace(' ','') == header.replace(' ',''):
                        colindex = i
        else:
            rowindex = j-1
            return rowindex, colindex

# NAME STRIP
def strip_index(name):
    indexes = ['_nxdual','_index','_rpi','_agilent','_mondrian','_haloht','_halo','_sureselect','_dual','_hht','_ss','_i','_r','_a','_m','_h']
    name = name.replace('-', '_').replace(' ', '')
    for i in indexes:
        name=name.split(i)[0]
    return name

def get_20158_info(client, project_name_swe):
    versions = {"01": ['Sample name Scilife', "Total reads per sample", "Sheet1","Passed=P/ not passed=NP*"],
            "02": ["Sample name (SciLifeLab)", "Total number of reads (Millions)","Sheet1",
              "Based on total number of reads after mapping and duplicate removal"],
            "03": ["Sample name (SciLifeLab)", "Total number of reads (Millions)","Sheet1",
              "Based on total number of reads after mapping and duplicate removal "],
            "05": ["Sample name (from Project read counts)", "Total number","Sheet1",
              "Based on total number of reads","Based on total number of reads after mapping and duplicate removal"],
            "06": ["Sample name (from Project read counts)", "Total number","Sheet1",
              "Based on total number of reads","Based on total number of reads after mapping and duplicate removal"]}
    info = {}
    feed = bcbio.google.spreadsheet.get_spreadsheets_feed(client, project_name_swe + '_20158', False)
    if len(feed.entry) != 0:
        ssheet = feed.entry[0].title.text
        version = ssheet.split(str('_20158_'))[1].split(' ')[0].split('_')[0]
        content, ws_key, ss_key = get_google_document(ssheet,  versions[version][2], client)
        dummy, P_NP_colindex = get_column(content, versions[version][3])
        dummy, No_reads_sequenced_colindex = get_column(content, versions[version][1])
        row_ind, scilife_names_colindex = get_column(content, versions[version][0])
        if (version=="05")| (version=="06"):
            dummy, P_NP_duprem_colindex = get_column(content, versions[version][4]) ## [version][4] for dup rem
        else:
            P_NP_duprem_colindex=''
        for j, row in enumerate(content):
            if (j > row_ind):
                try:
                    sci_name = str(row[scilife_names_colindex]).strip()
                    striped_name = strip_index(sci_name)
                    no_reads = str(row[No_reads_sequenced_colindex]).strip()
                    if (P_NP_duprem_colindex!='') and (str(row[P_NP_duprem_colindex]).strip()!=''):
                        status = str(row[P_NP_duprem_colindex]).strip()
                    else:
                        status = str(row[P_NP_colindex]).strip()
                    info[striped_name] = [status,no_reads]
                except:
                    pass
    return info

def get(project_ID):
    CREDENTIALS_FILE = os.path.join(os.environ['HOME'], 'opt/config/gdocs_credentials')
    CONFIG_FILE = os.path.join(os.environ['HOME'], 'opt/config/post_process.yaml')
    CONFIG = cl.load_config(CONFIG_FILE)
    client= make_client(CREDENTIALS_FILE)
    info = get_20158_info(client, project_ID)
    print info
    return info

