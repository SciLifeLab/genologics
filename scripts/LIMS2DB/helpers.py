#!/usr/bin/env python

def comp_dates(a, b):
	"""Dates in isoformat. Is a < b?"""
     	if int(a.replace('-','')) < int(b.replace('-','')):
       		return True
    	else:
         	return False


def delete_Nones(dict):
	"Deletes None type items from dict."
	new_dict = {}
       	for key, val in dict.items():
        	if val:
                       	new_dict[key] = val
    	if new_dict != {}:
           	return new_dict
