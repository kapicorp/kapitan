import json
import os

from kapitan.inputs import kadet
from kapitan.resources import jinja2_render_file

inventory = kadet.inventory()


def main():
    path = os.path.dirname(__file__) + "/../../templates"
    output = kadet.BaseObj()
    for file in inventory.parameters.dockerfiles:
        contents = jinja2_render_file([path], "Dockerfile", json.dumps(file))
        output.root["Dockerfile." + file.name] = contents
    return output
