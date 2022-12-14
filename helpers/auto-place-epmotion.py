"""
This script is being run automaticly upon entry to the placement page at the step "Normalization - EpMotion (Illumina DNA Prep v3.1)". 
The script will place samples onto the output-plate automatically sorting samples by project name first, then submitted sample id

Inpired by NSCs auto-place-prep.py (nsc-norway/lims/helpers/auto-place-prep.py)
That script was written to create new containers if the first is filled (ie if you have more than 96 samples).
For this step we only allow a maximum of 96 samples and a single output plate, so that function was not needed. 
Also, we want placement based on slightly different sorting criteria. 
Script is thus simplified to work with only one plate. Script also has a different sorting strategy (project name + lims id)

NOTE: sorting criteria can easily be modified through the list "input_list_sort"

author: Magnus Leithaug
"""
import sys
from genologics.lims import *
from genologics import config
import re

def main(process_id):
    
    # load instance, process id, step id and step placements

    lims = Lims(config.BASEURI, config.USERNAME, config.PASSWORD) 
    process = Process(lims, id=process_id)
    step = Step(lims, id=process_id)
    step.placements.get()

    # making list input_list_sort:   [project-name, last-digits-of-submitted-id, output-uri]
    # the first two entries in the list, project-name and submitted-id will be used for soring the list, while the output uri is used to obtain data
    # regular expression for the submitted sample id will extract the last digits in the id and converting it to num (str does not sort "correctly" using sorted method)

    input_list_sort = []
    for ii,oo in process.input_output_maps:
        if oo and oo['output-type'] == 'Analyte' and oo['output-generation-type'] == "PerInput":
            
            input = ii['uri']
            input_list_sort.append((
                input.samples[0].project.name,
                int(re.match('.*?([0-9]+)$', input.samples[0].id).group(1)),
                oo['uri']))

    # end script if more than 96 samples. No more than 96 samples can physically fit onto the Epmotion deck. Also this script only support one output plate

    if len(input_list_sort) > 96:
        print("You have entered the step with", len(input_list_sort), ", samples. Maximum for this step is 96 samples")
        sys.exit(1)

    # there is always one output container created as default. Storing that container in output_container 
    
    output_container = step.placements.selected_containers

    #  generate sample placements sorted according to project name first and sample id second. Storing placement info in placement variable
   
    placements = []
    outwell_index = -1
    for _,_,o in sorted(input_list_sort):
        outwell_index += 1
        outwell = "{}:{}".format("ABCDEFGH"[outwell_index % 8], 1 + outwell_index // 8)
        placements.append((o.stateless, (output_container[0], outwell)))  #why stateless? kept it from the original script

    # setting placements assigned above and placing a post to the lims through the api

    step.placements.set_placement_list(placements)
    step.placements.post()

main(sys.argv[1])