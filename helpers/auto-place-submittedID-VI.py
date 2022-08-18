import sys
from genologics.lims import *
from genologics import config
#from pprint import pprint

def main(process_id):
    lims = Lims(config.BASEURI, config.USERNAME, config.PASSWORD) 
    process = Process(lims, id=process_id)
    step = Step(lims, id=process_id)
    step.placements.get()
    inputs = process.all_inputs(unique=True, resolve=True)
    lims.get_batch(i.samples[0] for i in inputs)

    # One output container is created by default. This will iterate over that one container.
    
    output_containers_iter = iter(step.placements.selected_containers)

    # Making a list of output uri`s. Will be used for sorting later
    
    input_list = []
    for ii,oo in process.input_output_maps:
        if oo['output-generation-type'] == "PerInput":
            i = ii['uri']
            input_list.append((oo['uri']))

    # Assigning placements. Using input list without sorting. Default sorting is on submitted sample id.
    # Setting initial outwell_index to 999 to make loop request new container on first sample.

    placements = []
    niseks_plate = None
    outwell_index = 999
    for o in input_list:
        outwell_index += 1
        if outwell_index >= 96:
            try:
                output_container = next(output_containers_iter)
            except StopIteration:
                if not niseks_plate:
                    niseks_plate = next(iter(lims.get_container_types('96 well plate')))
                output_container = lims.create_container(niseks_plate)
            outwell_index = 0
        outwell = "{}:{}".format(
                "ABCDEFGH"[outwell_index % 8],
                1 + outwell_index // 8
                )
        placements.append((o.stateless, (output_container, outwell)))
    step.placements.set_placement_list(placements)
    step.placements.post()

main(sys.argv[1])