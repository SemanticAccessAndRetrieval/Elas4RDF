import glob
import os
from pathlib import Path
from timeit import default_timer as timer
from multiprocessing import Pool, Manager

import elasticsearch
import el_controller
from index import print_message


# extract name-space from an input URI
def get_name_space(triple_part, pre_flag):
    if pre_flag:
        n_space = triple_part.rsplit('#', 1)[0]
    else:
        n_space = triple_part.rsplit('/', 1)[0]

    return n_space


# main method for indexing - accepts an input folder of .ttl files
def baseline_index(input_folder):
    # bulk config - empirically set to 3500
    bulk_size = 3500
    prop_bulk_size = 3500
    bulk_actions = []
    prop_bulk_actions = []
    global config

    if (config.verbose):
        print("\t " + input_folder + ": started")

    # parse each .ttl file inside input folder
    for ttl_file in glob.glob(input_folder + '/*.ttl'):
        with open(ttl_file) as fp:

            line = fp.readline()
            while line:

                if "<" not in line:
                    line = fp.readline()
                    continue

                line = line.replace("<", "").replace(">", "").replace("\n", "")
                contents = line.split(" ", 2)

                if len(contents) < 3:
                    line = fp.readline()
                    continue

                # handle subject
                sub_keywords = contents[0].rsplit('/', 1)[-1].replace(":", "")
                sub_nspace = get_name_space(contents[0], False)

                # handle predicate
                if "#" not in contents[1]:
                    pred_keywords = contents[1].rsplit('/', 1)[-1].replace(":", "")
                    pred_nspace = get_name_space(contents[1], False)
                else:
                    pred_keywords = contents[1].rsplit('#', 1)[-1].replace(":", "")
                    pred_nspace = get_name_space(contents[1], True)

                # handle object
                if "\"" in contents[2]:
                    obj_keywords = contents[2].replace("\"", " ")[:-2]
                    obj_nspace = ""
                elif "/" in contents[2]:
                    obj_keywords = contents[2].rsplit('/', 1)[-1].replace(":", "")[:-2]
                    obj_nspace = get_name_space(contents[2], False)
                elif "#" in contents[2]:
                    obj_keywords = contents[2].rsplit('#', 1)[-1].replace(":", "")[:-2]

                # if predicate-property is included in ext_fields - build properties indexes
                if config.prop and contents[1] in config.ext_fields.values():

                    # get field-prop name
                    field_prop = {v: k for k, v in config.ext_fields.items()}[contents[1]]

                    # create a property - document
                    prop_doc = {"resource_terms": sub_keywords, field_prop: obj_keywords}

                    # add insert action
                    prop_action = {
                        "_index": field_prop,
                        '_op_type': 'index',
                        "_type": "_doc",
                        "_source": prop_doc
                    }

                    prop_bulk_actions.append(prop_action)
                    if len(prop_bulk_actions) > prop_bulk_size:
                        el_controller.bulk_action(prop_bulk_actions)
                        del prop_bulk_actions[0:len(prop_bulk_actions)]

                # create a triple - document
                doc = {"subjectKeywords": sub_keywords, "predicateKeywords": pred_keywords,
                       "objectKeywords": obj_keywords, "subjectNspaceKeys": sub_nspace,
                       "predicateNspaceKeys": pred_nspace, "objectNspaceKeys": obj_nspace}

                try:
                    # add insert action
                    action = {
                        "_index": config.base_index,
                        '_op_type': 'index',
                        "_type": "_doc",
                        "_source": doc
                    }

                    bulk_actions.append(action)
                    if len(bulk_actions) > bulk_size:
                        el_controller.bulk_action(bulk_actions)
                        del bulk_actions[0:len(bulk_actions)]

                except elasticsearch.ElasticsearchException as es:

                    print("Elas4RDF: Exception occured, skipping file: " + ttl_file)
                    if (config.verbose):
                        print(str(es))

                line = fp.readline()
                ####

        global finished_files
        global total_files
        finished_files.append(ttl_file)

       # print progress information
        if len(finished_files) == len(total_files):
            p_str = ""
        else:
            p_str = "\r"
        print("\t Files : " + str(len(finished_files)) + " / " +
              str(len(total_files)) + " , triples indexed: " + str(
            el_controller.count_docs(config.base_index)) + p_str,
              end="")

    # flush any action that is left inside the bulk actions
    el_controller.bulk_action(bulk_actions)
    el_controller.bulk_action(prop_bulk_actions)

    if (config.verbose):
        print("\t " + input_folder + ": finished")


def controller(config_f):
    global config
    config = config_f

    rdf_dir = config.rdf_dir

    # count.ttl files
    global total_files
    total_files = []
    for path in Path(rdf_dir).rglob('*.ttl'):
        total_files.append(str(path.absolute()))

    print_message.baseline_starting(config, str(len(total_files)))

    ttl_folders = []
    for ttl_folder in os.listdir(rdf_dir):
        ttl_folder = rdf_dir + "/" + ttl_folder
        if os.path.isdir(ttl_folder):
            ttl_folders += [os.path.join(ttl_folder, f) for f in os.listdir(ttl_folder)]

    start = timer()

    # deploy index instances (as indicated in indexing.instances in -config)
    manager = Manager()
    global finished_files
    finished_files = manager.list()
    p = Pool(config.instances)
    p.map(baseline_index, ttl_folders)

    end = timer()
    print_message.baseline_finised(config, str((end - start)))