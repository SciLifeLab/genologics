import codecs
from scilifelab.google import _to_unicode, _from_unicode
from pprint import pprint
from genologics.lims import *
from helpers import *
from genologics.lims_utils import *
from statusDB_utils import *
from genologics.config import BASEURI, USERNAME, PASSWORD
lims = Lims(BASEURI, USERNAME, PASSWORD)
import os
import couchdb
import bcbio.pipeline.config_loader as cl
import time
from datetime import date
config_file = os.path.join(os.environ['HOME'], 'opt/config/post_process.yaml')
db_conf = cl.load_config(config_file)['couch_db']
url = db_conf['maggie_login']+':'+db_conf['maggie_pass']+'@'+db_conf['maggie_url']+':'+str(db_conf['maggie_port'])
samp_db = couchdb.Server("http://" + url)['samples']

class ProjectDB():
        """Dictionary formated for building upt the project database on status db. Source of information
	come from diferent lims artifacts and processes. A datailed documentation of the source of all values
	is found in: 
	https://docs.google.com/a/scilifelab.se/document/d/1OHRsSI9btaBU4Hb1TiqJ5wwdRqUQ4BAyjJR-Nn5qGHg/edit#"""
        def __init__(self, project_id):
		proj_time = time.time()
                self.lims_project = Project(lims,id = project_id)
		self.preps = ProcessInfo(lims.get_processes(projectname = self.lims_project.name, type = AGRLIBVAL.values()))
		self.runs  = ProcessInfo(lims.get_processes(projectname = self.lims_project.name, type = SEQUENCING.values()))
                self.project={'source' : 'lims',
			'open_date' : self.lims_project.open_date,
			'entity_type' : 'project_summary',
                        'application' : None,
                        'project_name' : self.lims_project.name,
                        'project_id' : self.lims_project.id}
                self.udf_field_conv={'Name':'name',
                        #'Queued':'queued',
                        'Portal ID':'Portal_id',
                        'Sample type':'sample_type',
                        'Sequence units ordered (lanes)':'sequence_units_ordered_(lanes)',
                        'Sequencing platform':'sequencing_platform',
                        'Sequencing setup':'sequencing_setup',
                        'Library construction method':'library_construction_method',
                        'Bioinformatics':'bioinformatics',
                        'Disposal of any remaining samples':'disposal_of_any_remaining_samples',
                        'Type of project':'type',
                        'Invoice Reference':'invoice_reference',
                        'Uppmax Project Owner':'uppmax_project_owner',
                        'Custom Capture Design ID':'custom_capture_design_id',
                        'Customer Project Description':'customer_project_description',
                        'Project Comment':'project_comment',
                        'Delivery Report':'delivery_report'}
                self.basic_udf_field_conv = {'Reference genome':'reference_genome',
                        'Application':'application',
                        'Uppmax Project':'uppnex_id',
                        'Customer project reference':'customer_reference'}
                for key, val in self.lims_project.udf.items():
                        if self.udf_field_conv.has_key(key):
                                if self.project.has_key('details'):
                                        self.project['details'][self.udf_field_conv[key]] = val
                                else: self.project['details'] = {self.udf_field_conv[key] : val}
                        elif self.basic_udf_field_conv.has_key(key):
                                self.project[self.basic_udf_field_conv[key]] = val
                samples = lims.get_samples(projectlimsid = self.lims_project.id)
                self.project['no_of_samples'] = len(samples)
                if len(samples) > 0:
                        self.project['samples']={}
                        for samp in samples:
				samp_time = time.time()
                                sampDB = SampleDB(samp.id, self.project['project_name'], self.project['application'], self.preps.info, self.runs.info)
				print time.time() - samp_time, "samptime"
                                self.project['samples'][sampDB.name] = sampDB.obj
		self.project = delete_Nones(self.project)
		print time.time() - proj_time, "projtime"

class ProcessInfo():
	"""info = {24-8460:{'finish_date':'2013-04-20', 
                            'start_date',
                            'run_id':'24-8460',
                            'samples':{'P424_111':{in_art_id1 : [in_art1, out_art1],
                                                   in_art_id2: [in_art2, out_art2]},
                                       'P424_115': ...},
                                       ...},
                   '24-8480':...}"""

	def __init__(self, runs):
		self.info = self.get_run_info(runs)

        def get_run_info(self, runs):
                """input: A list of process type names. Eg 'Aggregate QC (Library Validation) 4.0'
		output: a dict with info about all processes of the type specified in runs
		which the projecthas got through."""
                run_info = {}
                for run in runs:
                        run_info[run.id] = {'start_date': run.date_run,'samples' : {}}
                        run_udfs = dict(run.udf.items())
                        try:
                                run_info[run.id]['run_id'] = run_udfs["Run ID"]
                        except:
                                pass
                        try:
                                run_info[run.id]['finish_date'] = run_udfs['Finish Date'].isoformat()
                        except:
                                run_info[run.id]['finish_date'] = None
                                pass
                        in_arts=[]
                        for IOM in run.input_output_maps:
                                in_art_id = IOM[0]['limsid']
                                in_art = Artifact(lims, id= in_art_id)
                                out_art_id = IOM[1]['limsid']
                                out_art = Artifact(lims, id= out_art_id)
                                samples = in_art.samples
                                if in_art_id not in in_arts:
                                        in_arts.append(in_art_id)
                                        for samp in samples:
                                                if not samp.name in run_info[run.id]['samples'].keys():
                                                        run_info[run.id]['samples'][samp.name] = {}
                                                run_info[run.id]['samples'][samp.name][in_art_id] = [in_art, out_art]
                return run_info



class SampleDB():
        """Dictionary formated for building up the samples in the project database on status db. Source of information
        come from diferent lims artifacts and processes. A datailed documentation of the source of all values
        is found in: 
        https://docs.google.com/a/scilifelab.se/document/d/1OHRsSI9btaBU4Hb1TiqJ5wwdRqUQ4BAyjJR-Nn5qGHg/edit#"""
        def __init__(self, sample_id, project_name, application = None, prep_info = [], run_info = []):
                self.lims_sample = Sample(lims, id = sample_id)
                self.name = self.lims_sample.name
		self.application = application
		self.outin, self.inout = make_sample_artifact_maps(self.name)
                self.obj={'scilife_name' : self.name}
                self.udf_field_conv = {'Name':'name',
                        'Progress':'progress',
                        'Sequencing Method':'sequencing_method',
                        'Sequencing Coverage':'sequencing_coverage',
                        'Sample Type':'sample_type',
                        'Reference Genome':'reference_genome',
                        'Pooling':'pooling',
                        'Application':'application',
                        'Read Length':'requested_read_length',
                        'Control?':'control',
                        'Sample Buffer':'sample_buffer',
                        'Units':'units',
                        'Customer Volume':'customer_volume',
                        'Color':'color',
                        'Customer Conc.':'customer_conc',
                        'Customer Amount (ug)':'customer_amount_(ug)',
                        'Customer A260:280':'customer_A260:280',
                        'Conc Method':'conc_method',
                        'QC Method':'qc_method',
                        'Extraction Method':'extraction_method',
                        'Customer RIN':'customer_rin',
                        'Sample Links':'sample_links',
                        'Sample Link Type':'sample_link_type',
                        'Tumor Purity':'tumor_purity',
                        'Lanes Requested':'lanes_requested',
                        'Customer nM':'customer_nM',
                        'Customer Average Fragment Length':'customer_average_fragment_length',
                        '-DISCONTINUED-SciLifeLab ID':'sciLifeLab_ID',
                        '-DISCONTINUED-Volume Remaining':'volume_remaining'}
                self.basic_udf_field_conv = {'Customer Sample Name':'customer_name',
                        'Reads Requested (millions)':'reads_requested_(millions)',
                        'Insert Size':'average_size_bp',
                        'Passed Initial QC':'incoming_QC_status'} 
                for key, val in self.lims_sample.udf.items():
			val=_to_unicode(_from_unicode(val))
                        if self.udf_field_conv.has_key(key):
                                if self.obj.has_key('details'):
                                        self.obj['details'][self.udf_field_conv[key]] = val
                                else: self.obj['details'] = {self.udf_field_conv[key] : val}
                        elif self.basic_udf_field_conv.has_key(key):
                                self.obj[self.basic_udf_field_conv[key]] = val
		runs = self.get_sample_run_metrics(run_info)
		if self.application == 'Finished library' :
			preps = self.get_initQC_preps_and_libval_finished_lib(prep_info)
		else:
			preps = self.get_initQC_preps_and_libval(prep_info)
		if preps:
			if preps.has_key('library_prep'):
                        	for prep in runs.keys():
                                	if preps['library_prep'].has_key(prep):
                                        	preps['library_prep'][prep]['sample_run_metrics'] = runs[prep]
				self.obj['library_prep'] = self.get_prep_leter(preps['library_prep'])
			if preps.has_key('initial_qc'):
                        	self.obj['initial_qc'] = preps['initial_qc']
	
        def get_initQC_preps_and_libval_finished_lib(self, AgrLibQC_info):
                """Input: AgrLibQC_info - instance of the ProcessInfo class with AGRLIBVAL processes as argument
                For each AGRLIBVAL process run on the sample, this function steps bacward in the artifact history of the 
                output artifact of the AGRLIBVAL process to find the folowing information:

                initial_qc/start_date           The date_run of the first of all INITALQC steps found for in the artifact 
                                                history of the output artifact of one of the AGRINITQC steps 
                initial_qc/finish_date          The date_run of the of the AGRINITQC step 

                Preps are  defined by the AGRINITQC step

                prep_status                     The qc_flag of the input artifact of process type AGRLIBVAL
                library_validation/start_date   First of all LIBVAL steps found for in the artifact history 
                                                of the output artifact of one of the AGRLIBVAL step 
                library_validation/finish_date  date-run of AGRLIBVAL step 
                average_size_bp                 udf ('Size (bp)') of the input artifact to the process AGRLIBVAL"""
                sample_runs = {}
		library_prep = {}
                for run_id, run in AgrLibQC_info.items():
                        if run['samples'].has_key(self.name):
                                for id , arts in run['samples'][self.name].items():
                                        inart = arts[0]
                                        outart = arts[1]
                                        history = get_analyte_hist(outart.id, self.outin, self.inout)
					sample_runs['initial_qc'] = self.get_initial_qc_dates(history)
                                        lib_val_dates = {'start_date': self.get_lib_val_start_dates(history),
                                                        'finish_date': run['start_date']}
                                        prep = {'prep_status':inart.qc_flag}
                                        if dict(inart.udf.items()).has_key('Size (bp)'):
                                                prep['average_size_bp'] = dict(inart.udf.items())['Size (bp)']
                                        if not library_prep.has_key('Finished'):
                                                library_prep['Finished'] = delete_Nones(prep)
						library_prep['Finished']['library_validation'] = {}
                                        library_prep['Finished']['library_validation'][run_id] = delete_Nones(lib_val_dates)
                sample_runs['library_prep'] = delete_Nones(library_prep)
                return delete_Nones(sample_runs)

        def get_initQC_preps_and_libval(self, AgrLibQC_info):
		"""Input: AgrLibQC_info - instance of the ProcessInfo class with AGRLIBVAL processes as argument.
		For each AGRLIBVAL process run on the sample, this function steps bacward in the artifact history of the 
		output artifact of the AGRLIBVAL process to find the folowing information:

		initial_qc/start_date 		The date_run of the first of all INITALQC steps found for in the artifact 
						history of the output artifact of one of the AGRINITQC steps 
		initial_qc/finish_date 		The date_run of the of the AGRINITQC step 

		Preps are  defined by the date of any PREPSTART step

		prep_status 			The qc_flag of the input artifact of process type AGRLIBVAL
		prep_start_date 		The date-run of the PREPSTART step 
		prep_finished_date 		The date-run of a PREPEND step.
		pre_prep_start_date 		The date-run of process 'Shear DNA (SS XT) 4.0'. Only for 
						'Exome capture' projects
		library_validation/start_date 	First of all LIBVAL steps found for in the artifact history 
						of the output artifact of one of the AGRLIBVAL step 
		library_validation/finish_date 	date-run of AGRLIBVAL step 
		average_size_bp 		udf ('Size (bp)') of the input artifact to the process AGRLIBVAL"""
                sample_runs = {}
		library_prep = {}
                for run_id, run in AgrLibQC_info.items():
                        if run['samples'].has_key(self.name):
                                for id , arts in run['samples'][self.name].items():
                                        inart = arts[0]
                                        outart = arts[1]
                                        history = get_analyte_hist(outart.id, self.outin, self.inout)
                                    	sample_runs['initial_qc'] = self.get_initial_qc_dates(history)
					lib_val_dates = {'start_date' : self.get_lib_val_start_dates(history),
                                                     	'finish_date' : run['start_date']}
                                        prep = {'prep_status' : inart.qc_flag}
                                        if dict(inart.udf.items()).has_key('Size (bp)'):
                                                size_bp = dict(inart.udf.items())['Size (bp)']
					else:
						size_bp = None
					libPrep = None
                                        for step, info in history.items():
                                                if info['type'] in PREPSTART.keys():
							if self.application !='Exome capture':
                                                        	libPrep = info
                                                        prep['prep_start_date'] = info['date']
                                                elif info['type'] in PREPEND.keys():
                                                        prep['prep_finished_date'] = info['date']
                                                elif info['type'] == '74':
                                                        libPrep = info
                                                        prep['pre_prep_start_date'] = info['date']
					if libPrep:
						if not library_prep.has_key(libPrep['id']):
							library_prep[libPrep['id']] = delete_Nones(prep)
							library_prep[libPrep['id']]['library_validation'] = {}
                                		library_prep[libPrep['id']]['library_validation'][run_id] = delete_Nones(lib_val_dates)
						library_prep[libPrep['id']]['library_validation'][run_id]['average_size_bp'] = size_bp
		sample_runs['library_prep'] = delete_Nones(library_prep)
                return delete_Nones(sample_runs)

        def get_prep_leter(self, prep_info):
                """Get preps and prep names; A,B,C... based on prep dates for sample_name. 
                Output: A dict where keys are prep_art_id and values are prep names."""
                dates = {}
                prep_info_new = {}
                preps_keys = map(chr, range(65, 65+len(prep_info)))
                if len(prep_info) == 1:
                        prep_info_new['A'] = prep_info.values()[0]
                else:
                        for key, val in prep_info.items():
                                dates[key] = val['prep_start_date']
                        for i, key in enumerate(sorted(dates,key= lambda x : dates[x])):
                                prep_info_new[preps_keys[i]] = prep_info[key]
                return prep_info_new


        def get_sample_run_metrics(self, SeqRun_info):
		"""Input: SeqRun_info - instance of the ProcessInfo class with SEQUENCING processes as argument
                For each SEQUENCING process run on the sample, this function steps bacward in the artifact history of the 
                input artifact of the SEQUENCING process to find the folowing information:

		dillution_and_pooling_start_date  	date-run of SEQSTART step
		sequencing_start_date 			date-run of SEQUENCING step
		sequencing_finish_date 			udf ('Finish Date') of SEQUENCING step
		sample_run_metrics_id 			The sample database (statusdb) _id for the sample_run_metrics 
							corresponding to the run, sample, lane in question.
		samp_run_met_id 			= lane_date_fcid_barcode			
							date and fcid: from udf ('Run ID') of the SEQUENCING step. 
							barcode: from reagent-lables of output artifact from SEQSTART step.
							lane: from the location of the input artifact to the SEQUENCING step	
		preps are defined as the id of the PREPSTART step in the artifact history. If appllication== Finished library, 
		prep is defined as "Finnished". These keys are used to connect the seqeuncing steps to the correct preps."""
                sample_runs = {}
                for id, run in SeqRun_info.items():
                        if run['samples'].has_key(self.name) and run.has_key('run_id'):
                                date = run['run_id'].split('_')[0]
                                fcid = run['run_id'].split('_')[3]
                                for id , arts in run['samples'][self.name].items():
                                        lane_art = arts[0]
                                        outart = arts[1]
                                        lane = lane_art.location[1].split(':')[0]
                                        history = get_analyte_hist(lane_art.id, self.outin, self.inout)
                                        for step , info in history.items():
                                                if info['type'] in SEQSTART.keys():
                                                        art = Artifact(lims, id=info['outart'])
							if len(art.reagent_labels) > 0:
                                                        	barcode = self.get_barcode(art.reagent_labels[0])
                                                        	samp_run_met_id = '_'.join([lane, date, fcid, barcode])
							else:
								samp_run_met_id = None
                                                        dict = {'dillution_and_pooling_start_date': info['date'],
                                                                'sequencing_start_date': run['start_date'],
                                                                'sequencing_finish_date': run['finish_date'],
                                                                'sample_run_metrics_id': find_sample_run_id_from_view(samp_db, samp_run_met_id) }
							dict = delete_Nones(dict)
                                                        key = None
                                                        if self.application == 'Finished library' :
                                                                key = 'Finished'
                                                        else:
                                                                for step , info in history.items():
                                                                        if info['type'] in PREPSTART.keys():
                                                                                key = info['id']
                                                        if key:
                                                                if not sample_runs.has_key(key): 
									sample_runs[key] = {}
                                                                sample_runs[key][samp_run_met_id] = dict
                return sample_runs

        def get_sample_status():
                """ongoing,passed,aborted"""
		##	Not yet implemented

        def get_barcode(self, name):
                """Extracts barcode from artifact.egent_labels"""
                return name.split('(')[1].strip(')')

        def get_initial_qc_dates(self, history):
                """Extracts run dates for processes of type AGRINITQC 
                from a history dict."""
                initial_qc_finish_date = None
                for step , info in history.items():
                        if (info['type'] in AGRINITQC.keys()) and info['date']:
                                if initial_qc_finish_date is None:
                                        initial_qc_finish_date = info['date']
                                elif comp_dates(initial_qc_finish_date, info['date']):
                                        initial_qc_finish_date = info['date']
		if initial_qc_finish_date:
                	initial_qc_start_date = initial_qc_finish_date
                	for step , info in history.items():
                        	if (info['type'] in INITALQC) and info['date']:
                                	if comp_dates(info['date'], initial_qc_start_date):
                                        	initial_qc_start_date = info['date']
                	return {'start_date' : initial_qc_start_date, 'finish_date' : initial_qc_finish_date}
		else: 
			return

        def get_lib_val_start_dates(self, history):
                """Extracts run dates for processes of type LIBVAL 
                from a history dict."""
                lib_val_start_date = None
                for step , info in history.items():
                        if info['type'] in LIBVAL.keys():
                                if lib_val_start_date == None:
                                        lib_val_start_date = info['date']
                                elif comp_dates(info['date'], lib_val_start_date):
                                        lib_val_start_date = info['date']
                return lib_val_start_date
