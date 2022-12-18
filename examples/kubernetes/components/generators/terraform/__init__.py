from kapitan.inputs.kadet import BaseObj, inventory

inv = inventory()


def main(input_params):
    obj = BaseObj()
    generator_root_paths = input_params.get("generator_root", "sections.tf").split(".")
    root = inv.parameters

    for path in generator_root_paths:
        root = root.get(path, {})

    for section_name, content in root.items():
        if section_name in ["resource", "data"]:
            for resource_name, content in content.items():
                obj.root["{}.tf".format(resource_name)][section_name][
                    resource_name
                ] = content
        else:
            obj.root["{}.tf".format(section_name)][section_name] = content
    return obj
