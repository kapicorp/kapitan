local elasticsearch = import "components/elasticsearch/elasticsearch.statefulset.jsonnet";
local kube = import "lib/kube.libjsonnet";
local kap = import "lib/kapitan.libjsonnet";
local inv = kap.inventory();

local es = {
    Cluster(name):: {
        local c = self,
        Name:: name,

        local args = {
            Args+:: { ClusterName:: c.Name },
        },
        "es-master": elasticsearch.MasterNode(self.Name + "-master") + args,
        "es-data": elasticsearch.DataNode(self.Name + "-data") + args,
        "es-client": elasticsearch.ClientNode(self.Name + "-client") + args,
        "es-discovery-svc": kube.Service("elasticsearch-discovery") { target_pod:: c["es-master"].spec.template, target_container_name:: "master" },
        "es-elasticsearch-svc": kube.Service("elasticsearch") { target_pod:: c["es-client"].spec.template, target_container_name:: "client", type: "NodePort" },
    },

    cluster: $.Cluster("cluster"),
};

std.prune(es.cluster)
