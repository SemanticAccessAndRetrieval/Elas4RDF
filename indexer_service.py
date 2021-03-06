import argparse
import json
import os
import sys, csv

import el_controller
import elasticsearch
from index import mappings, baseline, extended, print_message


# configuration file object
class Configuration(object):
    def __init__(self):
        self.base = True
        self.base_index = "bindex"
        self.inc_uris = True
        self.inc_nspace = False
        self.prop = False

        self.ext = False
        self.ext_index = ""
        self.ext_fields = {}
        self.ext_inc_sub = True
        self.ext_inc_pre = True
        self.ext_inc_obj = True

        self.dataset_id = ""
        self.rdf_dir = ""
        self.instances = 5
        self.elastic_address = "http://localhost"
        self.elastic_port = "9200"

        self.verbose = False


# initialize from configuration file
def init_config_file(cfile):
    if not os.path.isfile(cfile):
        print('Error, ' + '\'' + cfile + '\'' + ' does not exist.')
        sys.exit(-1)

    config = Configuration()
    with open(cfile) as tsvfile:
        tsvreader = csv.reader(tsvfile, delimiter="=")
        for line in tsvreader:

            # ignore empty lines
            if len(line) == 0:
                continue

            if line[0] == "index.id":
                config.dataset_id = line[1]

            elif line[0] == "index.base":
                if line[1] == "yes":
                    config.base = True
                elif line[1] == "no":
                    config.base = False
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)

            elif line[0] == "index.base.name":
                config.base_index = line[1]

            elif line[0] == "index.base.include_uri":
                if line[1] == "yes":
                    config.inc_uris = True
                elif line[1] == "no":
                    config.inc_uris = False
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)

            elif line[0] == "index.base.include_namespace":
                if line[1] == "yes":
                    config.inc_nspace = True
                elif line[1] == "no":
                    config.inc_nspace = False
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)

            elif line[0] == "index.ext":
                if line[1] == "yes":
                    config.ext = True
                elif line[1] == "no":
                    config.ext = False
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)

            elif line[0] == "index.ext.name":
                config.ext_index = line[1]

            elif line[0] == "index.ext.fields":
                if len(line[1].rsplit(" ")) == 0:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)
                for field_entry in line[1].rsplit(" "):
                    if len(field_entry.rsplit(";", 1)) == 0:
                        print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[
                            1] + ' not recognized.')
                        sys.exit(-1)
                    else:
                        contents = field_entry.rsplit(";", 1)
                        field_name = contents[0]
                        field = contents[1]
                        config.ext_fields[field_name] = field
                        config.prop = True

            elif line[0] == "index.ext.include_sub":
                if line[1] == "yes":
                    config.ext_inc_sub = True
                elif line[1] == "no":
                    config.ext_inc_sub = False
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)

            elif line[0] == "index.ext.include_pre":
                if line[1] == "yes":
                    config.ext_inc_pre = True
                elif line[1] == "no":
                    config.ext_inc_pre = False
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)

            elif line[0] == "index.ext.include_obj":
                if line[1] == "yes":
                    config.ext_inc_obj = True
                elif line[1] == "no":
                    config.ext_inc_obj = False
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)

            elif line[0] == "index.data":
                if os.path.isdir(line[1]):
                    config.rdf_dir = line[1]
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[
                        1] + ' not a proper folder.')
                    sys.exit(-1)

            elif line[0] == "index.instances":
                try:
                    config.instances = int(line[1])
                except ValueError:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[
                        1] + ' not an integer')
                    sys.exit(-1)

            elif line[0] == "elastic.address":
                config.elastic_address = line[1]

            elif line[0] == "elastic.port":
                try:
                    config.elastic_port = int(line[1])
                except ValueError:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[
                        1] + ' not an integer')
                    sys.exit(-1)

            elif line[0] == "verbose":
                if line[1] == "yes":
                    config.verbose = True
                elif line[1] == "no":
                    config.verbose = False
                else:
                    print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[0] + " " + line[
                        1] + ' not recognized.')
                    sys.exit(-1)

            else:
                print('Error,' + '\'' + cfile + '\'' + ' is not a proper config file: ' + line[
                    0] + ' not recognized.')
                sys.exit(-1)

    return config


# create the ElasticSearch indexes - mappings
def create_indexes(config):
    try:
        if config.base:
            # get mapping & create index
            base_map = mappings.get_baseline(config)
            el_controller.create_index(config.base_index, base_map)

            if config.prop:
                for field in config.ext_fields.keys():
                    prop_map = mappings.get_properties(field)
                    el_controller.create_index(field, prop_map)

        # create extended & properties indexes
        if config.ext:
            ext_map = mappings.get_extended(config)
            el_controller.create_index(config.ext_index, ext_map)

    except elasticsearch.ElasticsearchException as e:
        print('Elas4RDF error: could not create indexes: ' + str(e))
        exit(-1)


# starts indexing for baseline
def index_baseline(config):
    baseline.controller(config)


# starts indexing for extended
def index_extended(config):
    extended.controller(config)


# verifies properties-indexes exist before starting extended
def properties_exist(config):
    exist = True
    index_missing = []
    for field in config.ext_fields.keys():
        if not el_controller.index_exists(field):
            index_missing.append(field)
            exist = False

    if not exist:
        print('Elas4RDF error, could not create \'' + str(config.ext_index) + '\'.'
                                                                              ' Missing properties-index(es): ',
              index_missing, ". Start baseline indexing process again.")

    return exist


# create an output config for later use (e.g. from a search-service)
def output_properties(config):
    output_name = "output.json"
    output = open(output_name, "w")
    conf_dict = {}
    fields = {}

    if config.ext:
        index = config.ext_index
    else:
        index = config.base_index

    if config.inc_uris:
        fields["subjectKeywords"] = 1
        fields["predicateKeywords"] = 1
        fields["objectKeywords"] = 2

    if config.inc_nspace:
        fields["subjectNspaceKeys"] = 1
        fields["predicateNspaceKeys"] = 1
        fields["objectNspaceKeys"] = 1

    if config.ext:
        for ext_field in config.ext_fields.keys():
            if config.ext_inc_sub:
                fields[ext_field + "_sub"] = 1
            if config.ext_inc_pre:
                fields[ext_field + "_pre"] = 1
            if config.ext_inc_obj:
                fields[ext_field + "_obj"] = 1

    conf_dict["id"] = config.dataset_id
    conf_dict["index.name"] = index
    conf_dict["index.fields"] = fields

    output.write(json.dumps(conf_dict, indent=4, sort_keys=False))

    return os.path.abspath(output_name)


def main():
    # setting up arguments parser
    parser = argparse.ArgumentParser(description='\'Indexer for generating the baseline and/or extended index\'')
    parser.add_argument('-config', help='"specify the config file(.tsv)', required=True)
    args = vars(parser.parse_args())

    # read configuration file
    config = init_config_file(args['config'])

    # print verification message
    print_message.verification_message(config)

    # initialize & basic configuration
    try:
        el_controller.init(config.elastic_address, config.elastic_port)
    except elasticsearch.ElasticsearchException as e:
        print('Elas4RDF error: could not initialize Elasticsearch: ' + str(e))

    # create index mappings & structures
    create_indexes(config)

    # start indexing
    if config.base:
        index_baseline(config)
    if config.ext:
        if properties_exist(config):
            index_extended(config)
        else:
            exit(-1)

    # generate .config output file
    file_path = output_properties(config)

    print_message.finished(file_path)


if __name__ == "__main__":
    main()
