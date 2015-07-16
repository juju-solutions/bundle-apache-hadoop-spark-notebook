#!/usr/bin/env python3

import os
import time
import unittest

import yaml
import amulet


class Base(object):
    """
    Base class for tests for Apache Hadoop Bundle.
    """
    bundle_file = os.path.join(os.path.dirname(__file__), '..', 'bundle.yaml')
    profile_name = None

    @classmethod
    def deploy(cls):
        # classmethod inheritance doesn't work quite right with
        # setUpClass / tearDownClass, so subclasses have to manually call this
        cls.d = amulet.Deployment(series='trusty')
        with open(cls.bundle_file) as f:
            bun = f.read()
        profiles = yaml.safe_load(bun)
        # amulet always selects the first profile, so we have to fudge it here
        profile = {cls.profile_name: profiles[cls.profile_name]}
        cls.d.load(profile)
        cls.d.setup(timeout=9000)
        cls.d.sentry.wait()
        cls.hdfs = cls.d.sentry.unit['hdfs-master/0']
        cls.yarn = cls.d.sentry.unit['yarn-master/0']
        cls.slave = cls.d.sentry.unit['compute-slave/0']
        cls.secondary = cls.d.sentry.unit['secondary-namenode/0']
        cls.plugin = cls.d.sentry.unit['plugin/0']
        cls.client = cls.d.sentry.unit['client/0']

    @classmethod
    def reset_env(cls):
        # classmethod inheritance doesn't work quite right with
        # setUpClass / tearDownClass, so subclasses have to manually call this
        juju_env = amulet.helpers.default_environment()
        services = ['hdfs-master', 'yarn-master', 'compute-slave', 'secondary-namenode', 'plugin', 'client']

        def check_env_clear():
            state = amulet.waiter.state(juju_env=juju_env)
            for service in services:
                if state.get(service, {}) != {}:
                    return False
            return True

        for service in services:
            cls.d.remove(service)
        with amulet.helpers.timeout(300):
            while not check_env_clear():
                time.sleep(5)

    def test_hadoop_components(self):
        """
        Confirm that all of the required components are up and running.
        """
        hdfs, retcode = self.hdfs.run("pgrep -a java")
        yarn, retcode = self.yarn.run("pgrep -a java")
        slave, retcode = self.slave.run("pgrep -a java")
        secondary, retcode = self.secondary.run("pgrep -a java")
        client, retcode = self.client.run("pgrep -a java")

        # .NameNode needs the . to differentiate it from SecondaryNameNode
        assert '.NameNode' in hdfs, "NameNode not started"
        assert 'ResourceManager' in yarn, "ResourceManager not started"
        assert 'JobHistoryServer' in yarn, "JobHistoryServer not started"
        assert 'NodeManager' in slave, "NodeManager not started"
        assert 'DataNode' in slave, "DataServer not started"
        assert 'SecondaryNameNode' in secondary, "SecondaryNameNode not started"

        return hdfs, yarn, slave, secondary, client  # allow subclasses to do additional checks

    def test_hdfs_dir(self):
        """
        Validate admin few hadoop activities on HDFS cluster.
            1) This test validates mkdir on hdfs cluster
            2) This test validates change hdfs dir owner on the cluster
            3) This test validates setting hdfs directory access permission on the cluster

        NB: These are order-dependent, so must be done as part of a single test case.
        """
        output, retcode = self.client.run("su hdfs -c 'hdfs dfs -mkdir -p /user/ubuntu'")
        assert retcode == 0, "Created a user directory on hdfs FAILED:\n{}".format(output)
        output, retcode = self.client.run("su hdfs -c 'hdfs dfs -chown ubuntu:ubuntu /user/ubuntu'")
        assert retcode == 0, "Assigning an owner to hdfs directory FAILED:\n{}".format(output)
        output, retcode = self.client.run("su hdfs -c 'hdfs dfs -chmod -R 755 /user/ubuntu'")
        assert retcode == 0, "seting directory permission on hdfs FAILED:\n{}".format(output)

    def test_yarn_mapreduce_exe(self):
        """
        Validate yarn mapreduce operations:
            1) validate mapreduce execution - writing to hdfs
            2) validate successful mapreduce operation after the execution
            3) validate mapreduce execution - reading and writing to hdfs
            4) validate successful mapreduce operation after the execution
            5) validate successful deletion of mapreduce operation result from hdfs

        NB: These are order-dependent, so must be done as part of a single test case.
        """
        jar_file = '/usr/lib/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar'
        test_steps = [
            ('teragen',      "su ubuntu -c 'hadoop jar {} teragen  10000 /user/ubuntu/teragenout'".format(jar_file)),
            ('mapreduce #1', "su hdfs -c 'hdfs dfs -ls /user/ubuntu/teragenout/_SUCCESS'"),
            ('terasort',     "su ubuntu -c 'hadoop jar {} terasort /user/ubuntu/teragenout /user/ubuntu/terasortout'".
                format(jar_file)),
            ('mapreduce #2', "su hdfs -c 'hdfs dfs -ls /user/ubuntu/terasortout/_SUCCESS'"),
            ('cleanup',      "su hdfs -c 'hdfs dfs -rm -r /user/ubuntu/teragenout'"),
        ]
        for name, step in test_steps:
            output, retcode = self.client.run(step)
            assert retcode == 0, "{} FAILED:\n{}".format(name, output)


class TestScalable(unittest.TestCase, Base):
    profile_name = 'apache-core-batch-processing'

    @classmethod
    def setUpClass(cls):
        cls.deploy()

    @classmethod
    def tearDownClass(cls):
        cls.reset_env()

    def test_hadoop_components(self):
        """
        In addition to testing that the components are running where they
        are supposed to be, confirm that none of them are also running where
        they shouldn't be.
        """
        hdfs, yarn, slave, secondary, client = super(TestScalable, self).test_hadoop_components()

        # .NameNode needs the . to differentiate it from SecondaryNameNode
        assert '.NameNode' not in yarn, "NameNode should not be running on yarn-master"
        assert '.NameNode' not in slave, "NameNode should not be running on compute-slave"
        assert '.NameNode' not in secondary, "NameNode should not be running on secondary-namenode"
        assert '.NameNode' not in client, "NameNode should not be running on client"

        assert 'ResourceManager' not in hdfs, "ResourceManager should not be running on hdfs-master"
        assert 'ResourceManager' not in slave, "ResourceManager should not be running on compute-slave"
        assert 'ResourceManager' not in secondary, "ResourceManager should not be running on secondary-namenode"
        assert 'ResourceManager' not in client, "ResourceManager should not be running on client"

        assert 'JobHistoryServer' not in hdfs, "JobHistoryServer should not be running on hdfs-master"
        assert 'JobHistoryServer' not in slave, "JobHistoryServer should not be running on compute-slave"
        assert 'JobHistoryServer' not in secondary, "JobHistoryServer should not be running on secondary-namenode"
        assert 'JobHistoryServer' not in client, "JobHistoryServer should not be running on client"

        assert 'NodeManager' not in yarn, "NodeManager should not be running on yarn-master"
        assert 'NodeManager' not in hdfs, "NodeManager should not be running on hdfs-master"
        assert 'NodeManager' not in secondary, "NodeManager should not be running on secondary-namenode"
        assert 'NodeManager' not in client, "NodeManager should not be running on client"

        assert 'DataNode' not in yarn, "DataNode should not be running on yarn-master"
        assert 'DataNode' not in hdfs, "DataNode should not be running on hdfs-master"
        assert 'DataNode' not in secondary, "DataNode should not be running on secondary-namenode"
        assert 'DataNode' not in client, "DataNode should not be running on client"

        assert 'SecondaryNameNode' not in yarn, "SecondaryNameNode should not be running on yarn-master"
        assert 'SecondaryNameNode' not in hdfs, "SecondaryNameNode should not be running on hdfs-master"
        assert 'SecondaryNameNode' not in slave, "SecondaryNameNode should not be running on compute-slave"
        assert 'SecondaryNameNode' not in client, "SecondaryNameNode should not be running on client"


if __name__ == '__main__':
    unittest.main()
