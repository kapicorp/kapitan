from kapitan.inputs import kadet


def main(input_params):
    inventory = kadet.inventory()
    output = kadet.BaseObj()
    for key, value in inventory.parameters.input.items():
        output.root[key] = kadet.BaseObj.from_dict(value)
    return output
