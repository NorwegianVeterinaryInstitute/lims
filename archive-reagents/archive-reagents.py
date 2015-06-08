import sys
from genologics.lims import *
from genologics import config

def main(process_id):
    lims = Lims(config.BASEURI, config.USERNAME, config.PASSWORD) 
    step = Step(lims, id=process_id)
    for lot in step.reagent_lots:
        lot.get()
        lot.status = "ARCHIVED"
        lot.put()


if __name__ == "__main__":
    main(sys.argv[1])
