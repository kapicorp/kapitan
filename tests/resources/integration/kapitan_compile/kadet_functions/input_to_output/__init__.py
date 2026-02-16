# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from kapitan.inputs import kadet


def main(input_params):
    inventory = kadet.inventory()
    output = kadet.BaseObj()
    for key, value in inventory.parameters.input.items():
        output.root[key] = kadet.BaseObj.from_dict(value)
    return output
