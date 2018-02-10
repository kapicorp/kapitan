
{
  MySQLService(name): {
    apiVersion: "v1",
    kind: "Service",
    spec: {
      ports: [ 
        { name: "mysql", port: 3306 }, 
      ],
      selector: { app: name },
      clusterIP: "None"
    },

    metadata: {
      name: name,
      labels: { app: name },
    },

  },
}
