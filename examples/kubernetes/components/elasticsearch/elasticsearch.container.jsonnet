local kube = import "lib/kube.libjsonnet";

{
  Container(role, image):: kube.Container(role) {
    local transportPort = {
      name: "transport",
      protocol: "TCP",
      containerPort: 9300,
    },

    local clientPort = {
      name: "client",
      protocol: "TCP",
      containerPort: 9200,
    },

    image: image,

    ports: (if role == "client" then [clientPort, transportPort] else [transportPort]),
  },
}
