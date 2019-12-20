import os
import json
from kapitan.resources import jinja2_render_file
from kapitan.inputs import kadet

inventory = kadet.inventory()


def main():
    path = os.path.dirname(__file__) + "/../../templates"
    output = kadet.BaseObj()
    for file in inventory.parameters.dockerfiles:
        contents = jinja2_render_file([path], "Dockerfile", json.dumps(file))
        output.root["Dockerfile." + file.name] = contents
    return output
