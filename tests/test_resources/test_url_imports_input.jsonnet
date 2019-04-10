local kube = import "https://github.com/bitnami-labs/kube-libsonnet/raw/52ba963ca44f7a4960aeae9ee0fbee44726e481f/kube.libsonnet";

// A function that returns 2 k8s objects: a redis Deployment and Service
{
  nginx: kube.Container("redis") {
      image: "nginx:1:15.8",
      ports: [{containerPort: 80}],
  }
}