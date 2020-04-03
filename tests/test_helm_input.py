#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"helm input tests"
import os
import sys
import tempfile
import unittest

import yaml
from kapitan.cached import reset_cache
from kapitan.cli import main
from kapitan.inputs.helm import Helm

helm_binding_exists = True
try:
    from kapitan.inputs.helm.helm_binding import (
        ffi,
    )  # this statement will raise ImportError if binding not available
except ImportError:
    helm_binding_exists = False


@unittest.skipUnless(helm_binding_exists, "helm binding is not available")
class HelmInputTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.join("tests", "test_resources"))

    def test_render_chart(self):
        temp_dir = tempfile.mkdtemp()
        chart_path = "charts/acs-engine-autoscaler"
        helm = Helm(None, None, None)
        error_message = helm.render_chart(chart_path, temp_dir)
        self.assertFalse(error_message)
        self.assertTrue(
            os.path.isfile(os.path.join(temp_dir, "acs-engine-autoscaler", "templates", "secrets.yaml"))
        )
        self.assertTrue(
            os.path.isfile(os.path.join(temp_dir, "acs-engine-autoscaler", "templates", "deployment.yaml"))
        )

    def test_error_invalid_char_dir(self):
        chart_path = "non-existent"
        temp_dir = tempfile.mkdtemp()
        helm = Helm(None, None, None)
        error_message = helm.render_chart(chart_path, temp_dir)
        self.assertTrue("no such file or directory" in error_message)

    def test_compile_chart(self):
        temp = tempfile.mkdtemp()
        sys.argv = ["kapitan", "compile", "--output-path", temp, "-t", "acs-engine-autoscaler"]
        main()
        self.assertTrue(
            os.path.isfile(
                os.path.join(
                    temp,
                    "compiled",
                    "acs-engine-autoscaler",
                    "acs-engine-autoscaler",
                    "templates",
                    "secrets.yaml",
                )
            )
        )

    def test_compile_subcharts(self):
        temp = tempfile.mkdtemp()
        sys.argv = ["kapitan", "compile", "--output-path", temp, "-t", "istio"]
        main()
        self.assertTrue(os.path.isdir(os.path.join(temp, "compiled", "istio", "istio", "charts")))
        self.assertTrue(os.path.isdir(os.path.join(temp, "compiled", "istio", "istio", "templates")))

    def test_compile_multiple_targets(self):
        temp = tempfile.mkdtemp()
        sys.argv = [
            "kapitan",
            "compile",
            "--output-path",
            temp,
            "-t",
            "acs-engine-autoscaler",
            "nginx-ingress",
            "-p",
            "2",
        ]
        main()
        self.assertTrue(
            os.path.isfile(
                os.path.join(
                    temp,
                    "compiled",
                    "acs-engine-autoscaler",
                    "acs-engine-autoscaler",
                    "templates",
                    "secrets.yaml",
                )
            )
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(
                    temp, "compiled", "nginx-ingress", "nginx-ingress", "templates", "clusterrolebinding.yaml"
                )
            )
        )

    def test_compile_multiple_charts_per_target(self):
        temp = tempfile.mkdtemp()
        sys.argv = ["kapitan", "compile", "--output-path", temp, "-t", "nginx-istio"]
        main()
        self.assertTrue(os.path.isdir(os.path.join(temp, "compiled", "nginx-istio", "istio", "templates")))
        self.assertTrue(
            os.path.isdir(os.path.join(temp, "compiled", "nginx-istio", "nginx-ingress", "templates"))
        )

    def test_compile_with_helm_values(self):
        temp = tempfile.mkdtemp()
        sys.argv = ["kapitan", "compile", "--output-path", temp, "-t", "nginx-ingress"]
        main()
        controller_deployment_file = os.path.join(
            temp, "compiled", "nginx-ingress", "nginx-ingress", "templates", "controller-deployment.yaml"
        )
        self.assertTrue(os.path.isfile(controller_deployment_file))
        with open(controller_deployment_file, "r") as fp:
            manifest = yaml.safe_load(fp.read())
            name = manifest["metadata"]["name"]
            self.assertEqual(name, "-nginx-ingress-my-controller")

    def test_compile_with_helm_params(self):
        temp = tempfile.mkdtemp()
        sys.argv = ["kapitan", "compile", "--output-path", temp, "-t", "nginx-ingress-helm-params"]
        with open("inventory/targets/nginx-ingress-helm-params.yml", "r") as fp:
            manifest = yaml.safe_load(fp.read())
            helm_params = manifest["parameters"]["kapitan"]["compile"][0]["helm_params"]
            release_name = helm_params["release_name"]
            namespace = helm_params["namespace"]

        main()
        controller_deployment_file = os.path.join(
            temp,
            "compiled",
            "nginx-ingress-helm-params",
            "nginx-ingress",
            "templates",
            "controller-deployment.yaml",
        )

        self.assertTrue(os.path.isfile(controller_deployment_file))
        with open(controller_deployment_file, "r") as fp:
            manifest = yaml.safe_load(fp.read())
            container = manifest["spec"]["template"]["spec"]["containers"][0]
            property = container["args"][4]
            self.assertEqual(
                property, "--configmap={}/{}".format(namespace, release_name + "-nginx-ingress-my-controller")
            )

    def test_compile_with_refs(self):
        temp = tempfile.mkdtemp()
        sys.argv = ["kapitan", "compile", "--output-path", temp, "-t", "nginx-ingress", "--reveal"]
        main()
        controller_deployment_file = os.path.join(
            temp, "compiled", "nginx-ingress", "nginx-ingress", "templates", "controller-deployment.yaml"
        )
        self.assertTrue(os.path.isfile(controller_deployment_file))
        with open(controller_deployment_file, "r") as fp:
            manifest = yaml.safe_load(fp.read())
            args = next(
                iter(
                    c["args"]
                    for c in manifest["spec"]["template"]["spec"]["containers"]
                    if c["name"] == "nginx-ingress-my-controller"
                )
            )
            self.assertIn("--election-id=super_secret_ID", args)

    def tearDown(self):
        os.chdir("../../")
        reset_cache()
