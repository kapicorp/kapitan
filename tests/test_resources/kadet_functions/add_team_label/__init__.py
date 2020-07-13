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

def main(kadet_params):
    team_name = kadet_params.get("team_name", "no-owner")
    if "namespace" in kadet_params:
        namespace = kadet_params.get("namespace")
    else:
        raise ValueError("'namespace' key not found in 'kadet_params'")

    if "input_paths" in kadet_params:
        input_paths = kadet_params.get("input_paths")
    else:
        raise ValueError("'input_paths' key not found in 'kadet_params'")

    # get path where files have been compiled on this run
    target_name = inventory.parameters.kapitan.vars.target
    compile_path = kadet_params.get("compile_path")
    root_path = get_root_path(compile_path, target_name)

    all_objects = {}
    for ip in input_paths:
        output = kadet.BaseObj()

        ip_file_path = os.path.join(root_path, target_name, ip)
        for file in glob.glob(ip_file_path + "/*.yaml", recursive=True):
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
