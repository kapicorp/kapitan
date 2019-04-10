local kube = import "https://github.com/bitnami-labs/kube-libsonnet/raw/52ba963ca44f7a4960aeae9ee0fbee44726e481f/kube.libsonnet";

// nginx container
{
  nginx: kube.Container("nginx") {
      image: "nginx:1:15.8",
      ports: [{containerPort: 80}],
  }
}