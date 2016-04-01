# Apache Hadoop with Spark and IPython Notebook

The IPython Notebook is an interactive computational environment in which you
can combine code execution, rich text, mathematics, plots, and rich media to
interact with your data backed by an Apache Hadoop + Spark cluster.

This bundle is a 7 node cluster designed to scale out. Built around Apache
Hadoop components, it contains the following units:

  * NameNode (HDFS)
  * ResourceManager (Yarn)
  * Slaves (DataNode and NodeManager)
  * Client (example and node for manually running jobs from)
    - Plugin (colocated on the Spark unit)
    - Notebook (colocated on the Spark unit)

Deploying this bundle gives you a fully configured and connected Apache Hadoop
cluster on any supported cloud, which can be easily scaled to meet workload
demands.


## Usage

Deploy this bundle using juju-quickstart:

    juju quickstart apache-hadoop-spark-notebook

See `juju quickstart --help` for deployment options, including machine
constraints and how to deploy a locally modified version of the
apache-hadoop-spark-notebook bundle.yaml.

The default bundle deploys three slave nodes and one node of each of
the other services. To scale the cluster, use:

    juju add-unit slave -n 2

This will add two additional slave nodes, for a total of five.


### Verify the deployment

The services provide extended status reporting to indicate when they are ready:

    juju status --format=tabular

This is particularly useful when combined with `watch` to track the on-going
progress of the deployment:

    watch -n 0.5 juju status --format=tabular

The charm for each core component (namenode, resourcemanager, spark)
also each provide a `smoke-test` action that can be used to verify that each
component is functioning as expected.  You can run them all and then watch the
action status list:

    juju action do namenode/0 smoke-test
    juju action do resourcemanager/0 smoke-test
    juju action do spark/0 smoke-test
    watch -n 0.5 juju action status

Eventually, all of the actions should settle to `status: completed`.  If
any go instead to `status: failed` then it means that component is not working
as expected.  You can get more information about that component's smoke test:

    juju action fetch <action-id>


### Access the IPython Notebook web interface

Access the notebook web interface at
http://{spark_unit_ip_address}:8880. The ip address can be found by running
`juju status spark/0 | grep public-address`.


## Contact Information

- <bigdata-dev@lists.launchpad.net>


## Help

- [Juju mailing list](https://lists.ubuntu.com/mailman/listinfo/juju)
- [Juju community](https://jujucharms.com/community)
