
Scripts in the Genologics Package
=================================
Short usage descriptions for the scripts in the Genologics Package.

zebra_barcodes.py
-----------------
Automated help message generated from running zebra_barcodes.py with the --help flag::

	usage: zebra_barcodes.py [-h] [--container_id] [--operator_and_date]
	                         [--container_name] [--process_name] [--copies COPIES]
	                         [--pid PID] [--log LOG] [--use_printer]
	                         [--hostname HOSTNAME] [--destination DESTINATION]
	                         [--no_prepend]
	
	Print barcodes on zebra barcode printer, different label types available.
	Information is fetched from Clarity LIMS.
	
	optional arguments:
	  -h, --help            show this help message and exit
	  --container_id        Print container id label in both barcode format and
	                        human readable.
	  --operator_and_date   Print label with both operator and todays date.
	  --container_name      Print label with human readablecontainer name (user
	                        defined)
	  --process_name        Print label with human readableprocess name
	  --copies COPIES       Number of printout copies, only used if neither
	                        container_name nor container_id type labels are
	                        printed. In that case, print one label of each type
	                        for each container.
	  --pid PID             The process LIMS id.
	  --log LOG             File name to use as log file
	  --use_printer         Print file on default or supplied printer using lp
	                        command.
	  --hostname HOSTNAME   Hostname for lp CUPS server.
	  --destination DESTINATION
	                        Name of printer.
	  --no_prepend          Do not prepend old log, useful when ran locally

generate_script_docs.py
-----------------------
Automated help message generated from running generate_script_docs.py with the --help flag::

	usage: generate_script_docs.py [-h]
	
	Generates basic documentation on all scripts contained in the scripts folder.
	Used instead of sphinx extension since readthedocs build failed on genologics
	imports.
	
	optional arguments:
	  -h, --help  show this help message and exit

