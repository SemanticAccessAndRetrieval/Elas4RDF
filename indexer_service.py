import argparse
import glob
import multiprocessing
import os
import re
import sys, csv
from timeit import default_timer as timer

import el_controller, mappings

# configuration file object
class Configuration(object):
    def __init__(self):
        self.base_index = "bindex"
        self.inc_uris = True
        self.inc_nspace = False

        self.ext = False
        self.ext_index = ""
        self.ext_fields = {}
        self.ext_inc_sub = True
        self.ext_inc_obj = True

        self.rdf_dir = ""
        self.elastic_address = "http://localhost"
        self.elastic_port = "9200"


# initialize from configuration file
def init_config_file(cfile):
    config = Configuration()
    with open(cfile) as tsvfile:
        tsvreader = csv.reader(tsvfile, delimiter="\t")
        for line in tsvreader:
            if line[0] == "indexing.base.name":
                config.base_index = line[1]

            elif line[0] == "indexing.base.include_uri":
                if line[1] == "yes":
                    config.inc_uris = True
                elif line[0] == "no":
                    config.inc_uris = False
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)

            elif line[0] == "indexing.base.include_namespace":
                if line[1] == "yes":
                    config.inc_nspace = True
                elif line[1] == "no":
                    config.inc_nspace = False
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)

            elif line[0] == "indexing.extend":
                if line[1] == "yes":
                    config.ext = True
                elif line[1] == "no":
                    config.ext = False
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)


            elif line[0] == "indexing.ext.name":
                config.ext_index = line[1]

            elif line[0] == "indexing.ext.fields":
                if len(line[1].rsplit(" ", 1)) == 0:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)
                for field_entry in line[1].rsplit(" ", 1):
                    if len(field_entry.rsplit(";", 1)) == 0:
                        print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[
                            1] + ' not recognized.')
                        sys.exit(-1)
                    else:
                        contents = field_entry.rsplit(";", 1)
                        field_name = contents[0]
                        field = contents[1]
                        config.ext_fields[field_name] = field

            elif line[0] == "indexing.ext.include_sub":
                if line[1] == "yes":
                    config.ext_inc_sub = True
                elif line[1] == "no":
                    config.ext_inc_sub = False
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)

            elif line[0] == "indexing.ext.include_obj":
                if line[1] == "yes":
                    config.ext_inc_obj = True
                elif line[1] == "no":
                    config.ext_inc_obj = False
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)

            elif line[0] == "indexing.data":
                if not os.path.isdir(line[1]):
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[
                        1] + ' not a proper folder.')
                    sys.exit(-1)
                else:
                    config.rdf_dir = line[1]

            elif line[0] == "elastic.address":
                config.elastic_address = line[1]

            elif line[0] == "elastic.port":
                config.elastic_port = line[1]

            else:
                print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[
                    0] + ' not recognized.')
                sys.exit(-1)

    return config


# create the ElasticSearch indexes - mappings
def create_indexes(config):
    # get mapping & create index
    base_map = mappings.get_baseline(config)
    el_controller.create_index(config.base_index, base_map)

    if config.ext:
        ext_map = mappings.get_extended(config)
        el_controller.create_index(config.ext_index, ext_map)


def main():
    # setting up arguments parser
    parser = argparse.ArgumentParser(description='\'Indexer for generating the baseline and/or extended index\'')
    parser.add_argument('-config', help='"specify the .config file', required=True)
    args = vars(parser.parse_args())

    # read configuration file
    config = init_config_file(args['config'])

    # initialize & basic configuration
    el_controller.init(config.elastic_address, config.elastic_port)
    create_indexes(config)


if __name__ == "__main__":
    main()