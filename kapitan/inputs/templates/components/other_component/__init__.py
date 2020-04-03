from kapitan.inputs import kadet

inv = kadet.inventory()

name = "other_component"
labels = kadet.BaseObj.from_dict({"app": name})


def main():
    output = kadet.BaseObj()
    output.root.my_kadet_component = name
    output.root.labels = labels
    return output
