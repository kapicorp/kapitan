local kube = import "lib/kube.libjsonnet";
local kap = import "lib/kapitan.libjsonnet";
local containers = import "./elasticsearch.container.jsonnet";
local capabilities = ["IPC_LOCK", "SYS_RESOURCE"];
local inv = kap.inventory();

local init_container = {
  name: "sysctl",
  image: "busybox",
  imagePullPolicy: "IfNotPresent",
  command: ["sysctl", "-w", "vm.max_map_count=262144"],
  securityContext: {
    privileged: true,
  },
};

{
  local inv_base = inv.parameters.elasticsearch,
  local base = {
    StatefulSet(name, role): kube.StatefulSet(name) {
      Args:: {
        Name:: name,
        Role:: role,
        ClusterName:: error "please define a cluster name",
        Image:: inv_base.roles[role].image,
        Replicas:: inv_base.roles[role].replicas,
        NumberOfMasters:: inv_base.roles[role].masters,
        JavaOPTS:: inv_base.roles[role].java_opts,
        Envs:: {
          NAMESPACE: { fieldRef: { fieldPath: "metadata.namespace" } },
          NODE_NAME: { fieldRef: { fieldPath: "metadata.name" } },
          CLUSTER_NAME: args.ClusterName,
          NUMBER_OF_MASTERS: args.NumberOfMasters,
          NODE_MASTER: "false",
          NODE_INGEST: "false",
          NODE_DATA: "false",
          HTTP_ENABLE: "false",
          ES_JAVA_OPTS: args.JavaOPTS,
        },
      },
      local args = self.Args,

      metadata+: {
        labels+: { role: role },
      },
      spec+: {
        replicas: args.Replicas,
        template+: {
          spec+: {
            initContainers+: [init_container],
            containers_+: {
              role: containers.Container(args.Role, args.Image) + $.SecurityContext(false, capabilities) { env_+: args.Envs },
            },
          },
        },
      },
    },

  },
  SecurityContext(privileged=true, cap_add=[], cap_remove=[]): {
    securityContext+: {
      privileged: privileged,
      capabilities+: {
        add: cap_add,
        remove: cap_remove,
      },
    },
  },

  MasterNode(name):: base.StatefulSet(name, "master") {
    Args+:: { Envs+:: { NODE_MASTER: "true" } },
  },

  DataNode(name):: base.StatefulSet(name, "data") {
    Args+:: { Envs+:: { NODE_DATA: "true" } },
  },

  ClientNode(name):: base.StatefulSet(name, "client") {
    Args+:: { Envs+:: { HTTP_ENABLE: "true" } },
  },

  IngestNode(name):: base.StatefulSet(name, "ingest") {
    Args+:: { Envs+:: { NODE_INGEST: "true" } },
  },
}
