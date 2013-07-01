import codecs
from pprint import pprint
from genologics.lims import *
from statusDB_utils import *
from genologics.config import BASEURI, USERNAME, PASSWORD
lims = Lims(BASEURI, USERNAME, PASSWORD)
import os
import couchdb
import bcbio.pipeline.config_loader as cl
import time
config_file = os.path.join(os.environ['HOME'], 'opt/config/post_process.yaml')
db_conf = cl.load_config(config_file)['couch_db']
url = db_conf['maggie_login']+':'+db_conf['maggie_pass']+'@'+db_conf['maggie_url']+':'+str(db_conf['maggie_port'])
samp_db = couchdb.Server("http://" + url)['samples']

class Lims2DB():
        def get_sample_status():
                """ongoing,passed,aborted"""

        def get_preps(self, sample_name):
                """Get preps and prep names; A,B,C... based on prep dates for sample_name. 
                Output: A dict where keys are prep_art_id and values are prep names."""
                dates = {}
                preps = {}
                artifacts = lims.get_artifacts(sample_name = sample_name, process_type = 'mRNA Purification, Fragmentation & cDNA synthesis (TruSeq RNA) 4.0')
                preps_keys = map(chr, range(65, 65+len(artifacts)))
                for art in artifacts:
                        dates[art.id] = art.parent_process.date_run
                for i, key in enumerate(sorted(dates,key= lambda x : dates[x])):
                        preps[key] = preps_keys[i]
                return preps

        def get_prep_status(self, sample_name, prep_art_id):
                """prep_art_id, artifact instance with parent process: 
                mRNA Purification, Fragmentation & cDNA synthesis (TruSeq RNA) 4.0"""
                status = {}
                average_size_bp = {}
                artifacts = lims.get_artifacts(sample_name = sample_name, process_type = 'CA Purification')
                for art in artifacts:
                        history, id_list = self.get_analyte_hist(art, sample_name)
			print history	
			print len(history)
			print sample_name
                        if prep_art_id in id_list:
                                try:
                                        average_size_bp[art.id] = dict(art.udf.items())['Size (bp)']
                                        status[art.id] = [art.qc_flag, art.parent_process.date_run]
                                except:
                                        pass
                                        print 'Size (bp)missing'
                return status, average_size_bp

        def get_analyte_hist(self, analyte, sample_name):
                """Makes a historymap of an analyte. sample_name has to be 
                given since the analyte can be a pool of many samples.
                Input:  Analyte instance and related sample name
                Output: List of dicts."""
                history = []
                id_list = []
                while analyte:
                        step = {'out': analyte}
                        id_list.append(analyte.id)
                        try:
                                step['process'] = analyte.parent_process
                                id_list.append(analyte.parent_process.type.id)
                                id_list.append(analyte.parent_process.id)
                        except:
                                pass
                        inarts = analyte.input_artifact_list()
                        analyte = None
                        if len(inarts) > 0:
                                for id in inarts:
                                        inart = Artifact(lims, id = id)
                                        for samp in inart.samples:
                                                if samp.name == sample_name:
                                                        step['in'] = inart
                                                        analyte = inart
                        history.append(step)
                return history, id_list

        def make_srm_id(self, lane_art, run, sample_name):
                """Get sample_run_metrics id for sample: sample_name
                run on lane: lane_art. Where lane_art is an artifact 
                instance with parent process type: Cluster Generation 
                (Illumina SBS) 4.0"""
                try:
                        inf = dict(run.udf.items())["Run ID"].split('_')
                        DATE = inf[0]
                        FCID = inf[3]
                        print DATE
                        print FCID
                        history, id_list = self.get_analyte_hist(lane_art, sample_name)
			print len(history)
			print history
                        for step in history:
                                if step.has_key('process'):
                                        if step['process'].type.name == 'Library Normalization (Illumina SBS) 4.0':
                                                BARCODE = self.get_barcode(step['out'].reagent_labels[0])
                                                print BARCODE
                                                break
                        LANE = lane_art.location[1].split(':')[0]
                        print LANE
                        return '_'.join([LANE,DATE,FCID,BARCODE])
                except:
                        print "udfs missing in sequencing process"
                        return None


        def get_barcode(self, name):
                return name.split('(')[1].strip(')')

        def get_sample_runs(self, sample_name, project_name):
                print 'get_sample_runs'
                runs_dict = {}
                lane_artifacts = lims.get_artifacts(sample_name = sample_name, process_type = 'Cluster Generation (Illumina SBS) 4.0',type='Analyte')
                print lane_artifacts
                for art in lane_artifacts: ## for varje pool
                        print art.id
                        runs = lims.get_processes(inputartifactslimsid = art.id ,type = 'Illumina Sequencing (Illumina SBS) 4.0', projectname = project_name)
                        runs_dict[art.id]={}
                        for run in runs: ## for varje korning av poolen
                                print run
                                runs_dict[art.id][run.id] = self.make_srm_id(art ,run , sample_name)
                return runs_dict

        def get_output_analytes(self, process_id):
                """Looks for output analytes of a process.
                Input:  Any process id
                Output: A list of artifact ids"""
                process = Process(lims, id = process_id)
                analyte_ids = []
                for map in process.input_output_maps:
                        if map[1]['output-type'] == 'Analyte':
                                analyte_ids.append(map[1]['limsid'])
                return analyte_ids


class ProjectDB(Lims2DB):
        """Convert project-udf-fields to project-couchdb-fields"""
        def __init__(self, project_id):
                TT = time.time()
                self.lims_project = Project(lims,id = project_id)
                self.project={'entity_type' : 'project_summary',
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
                samples = lims.get_samples(projectlimsid=self.lims_project.id)
                self.project['no_of_samples'] = len(samples)
                if len(samples) > 0:
                        self.project['samples']={}
                        for samp in samples:
                                t1 = time.time()##
                                sampDB = SampleDB(samp.id, self.project['project_name'], self.project['application'])
                                print time.time() - t1, "get samp"##
                                self.project['samples'][sampDB.name] = sampDB.obj
                print time.time() - TT, "projjjjjjj"##

class SampleDB(Lims2DB):
        def __init__(self, sample_id, project_name, application = None):
                self.lims_sample = Sample(lims, id = sample_id)
                self.name = self.lims_sample.name
                self.proj = self.lims_sample.project
                self.project_name = project_name
                self.project_application = application
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
                        'Passed Library QC':'prep_status',
                        '-DISCONTINUED-SciLifeLab ID':'sciLifeLab_ID',
                        '-DISCONTINUED-Volume Remaining':'volume_remaining'}
                self.basic_udf_field_conv = {'Customer Sample Name':'customer_name',
                        'Reads Requested (millions)':'reads_requested_(millions)',
                        'Insert Size':'average_size_bp',
                        'Passed Initial QC':'incoming_QC_status'} ## True/False instead of P/NP. OK? 
                for key, val in self.lims_sample.udf.items():
                        val = str(val)
                        if self.udf_field_conv.has_key(key):
                                if self.obj.has_key('details'):
                                        self.obj['details'][self.udf_field_conv[key]] = val
                                else: self.obj['details'] = {self.udf_field_conv[key] : val}
                        elif self.basic_udf_field_conv.has_key(key):
                                self.obj[self.basic_udf_field_conv[key]] = val
                t0 = time.time()##
                runs = self.get_sample_runs(self.name,self.project_name)
                print runs
                print time.time() - t0, "get runs"##
                t0 = time.time()##
                preps = self.get_preps(self.name)
                print preps
                print time.time() - t0, "get preps"##
                if len(runs) + len(preps) > 0:
                        self.obj['library_prep'] = {}
                        if self.project_application == 'Finished library':
                                self.obj['library_prep']['A'] = {}
                                for in_art_id, sample_runs in runs.items():
                                        for sample_run_name in sample_runs.values():
                                                t0 = time.time()##
                                                sample_run_key = str(find_sample_run_id_from_view(samp_db, sample_run_name))
                                                print time.time() - t0, "get runid"##
                                                try:
                                                        self.obj['library_prep']['A']['sample_run_metrics'][sample_run_name] = sample_run_key
                                                except:
                                                        self.obj['library_prep']['A']['sample_run_metrics'] = {sample_run_name : sample_run_key }
                        elif self.project_application:
                                for id, prep in preps.items():
                                        status, size_bp  = self.get_prep_status(self.name, id)
                                        self.obj['library_prep'][prep] = {'lims_id' : id}
                                        if status != {}:
                                                self.obj['library_prep'][prep]['prep_status'] = status
                                        if status != {}:
                                                self.obj['library_prep'][prep]['average_size_bp'] = size_bp
                                        for in_art_id, sample_runs in runs.items():
                                                history, id_list = self.get_analyte_hist(Artifact(lims,id = in_art_id), self.name)
                                                if id in id_list:
                                                        for sample_run_name in sample_runs.values():
                                                                        sample_run_key = find_sample_run_id_from_view(samp_db, sample_run_name)
                                                                        try:
                                                                                self.obj['library_prep'][prep]['sample_run_metrics'][sample_run_name] = sample_run_key
                                                                        except:
                                                                                self.obj['library_prep'][prep]['sample_run_metrics'] = {sample_run_name : sample_run_key }


