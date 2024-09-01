import os
import json
from kapitan.resources import jinja2_render_file, yaml_load
from kapitan.inputs import kadet
import glob
import yaml
import time

inventory = kadet.inventory()


def set_team_name(obj, team_name):
    obj.root.metadata["labels"]["team_name"] = team_name
    return obj


def set_namespace(obj, namespace):
    obj.root.metadata["namespace"] = namespace
    return obj


def get_root_path(path, target_name):
    drive, tail = os.path.split(path)
    if tail == target_name:
        return drive
    else:
        return get_root_path(drive, target_name)


def get_post_process_input_output_path(post_process_input):
    for i in inventory.parameters.kapitan.compile:
        if i.name == post_process_input:
            return i.output_path
    raise ValueError("'post_process_input' {post_process_input} not found")


def main(input_params):
    team_name = input_params.get("team_name", "no-owner")
    if "namespace" in input_params:
        namespace = input_params.get("namespace")
    else:
        raise ValueError("'namespace' key not found in 'input_params'")

    if "post_process_inputs" in input_params:
        post_process_inputs = input_params.get("post_process_inputs")
    else:
        raise ValueError("'post_process_inputs' key not found in 'input_params'")

    # get path where files have been compiled on this run
    target_name = inventory.parameters.kapitan.vars.target
    compile_path = input_params.get("compile_path")
    root_path = get_root_path(compile_path, target_name)

    all_objects = {}
    for post_process_input in post_process_inputs:
        output = kadet.BaseObj()
        p = get_post_process_input_output_path(post_process_input)
        dir_file_path = os.path.join(root_path, target_name, p)
        for file in glob.glob(dir_file_path + "/*.yaml", recursive=True):
            # remove file extension
            file_name = os.path.basename(file).replace(".yaml", "")
            with open(file) as fp:
                yaml_stream = yaml.safe_load_all(fp)
                objects_for_file = []
                for obj in yaml_stream:
                    o = kadet.BaseObj.from_dict(obj)
                    o = set_team_name(o, team_name)
                    o = set_namespace(o, namespace)
                    objects_for_file.append(o)
                all_objects.update({file_name: objects_for_file})
            fp.close()

    output = kadet.BaseObj()
    for file_name, obj in all_objects.items():
        output.root[file_name] = obj
    return output
