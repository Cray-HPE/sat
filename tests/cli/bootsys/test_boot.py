"""
Tests for common bootsys code.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""
from io import StringIO
import json
import logging
from textwrap import dedent
from unittest.mock import call, MagicMock, Mock, patch

from paramiko.ssh_exception import SSHException, NoValidConnectionsError

from sat.cli.bootsys.power import IPMIPowerStateWaiter
from sat.cli.bootsys.mgmt_boot_power import SSHAvailableWaiter, KubernetesPodStatusWaiter, \
    CephHealthWaiter, HSNBringupWaiter, HSNPort, BGPSpineStatusWaiter, StateError, restart_ceph_services
from tests.common import ExtendedTestCase


class WaiterTestCase(ExtendedTestCase):
    def setUp(self):
        self.mock_time_monotonic = patch('sat.cli.bootsys.waiting.time.monotonic').start()
        self.mock_time_sleep = patch('sat.cli.bootsys.waiting.time.sleep').start()

        self.members = ['groucho', 'chico', 'harpo', 'zeppo']
        self.timeout = 10
        self.username = 'user'
        self.password = 'pass'

    def tearDown(self):
        patch.stopall()


class TestIPMIPowerStateWaiter(WaiterTestCase):
    def setUp(self):
        self.mock_subprocess_run = patch('sat.cli.bootsys.power.subprocess.run').start()
        self.mock_subprocess_run.return_value.stdout = 'Chassis power is on'
        self.mock_subprocess_run.return_value.returncode = 0

        super().setUp()

    def test_sending_ipmi_commands(self):
        """Test that the waiter sends IPMI commands if desired"""
        waiter = IPMIPowerStateWaiter(self.members, 'on', self.timeout, self.username, self.password,
                                      send_command=True)

        waiter.pre_wait_action()
        self.mock_subprocess_run.assert_called()

    def test_not_sending_ipmi_commands(self):
        """Test that the waiter does not sends IPMI commands if not desired"""
        waiter = IPMIPowerStateWaiter(self.members, 'on', self.timeout, self.username, self.password,
                                      send_command=False)
        waiter.pre_wait_action()
        self.mock_subprocess_run.assert_not_called()

    def test_ipmi_is_completed(self):
        """Test that IPMI command is complete in the desired state"""
        waiter = IPMIPowerStateWaiter(self.members, 'on', self.timeout, self.username, self.password)
        for member in self.members:
            self.assertTrue(waiter.member_has_completed(member))

    def test_ipmi_is_not_completed(self):
        """Test that IPMI command is incomplete when not in the desired state"""
        waiter = IPMIPowerStateWaiter(self.members, 'off', self.timeout, self.username, self.password)
        for member in self.members:
            self.assertFalse(waiter.member_has_completed(member))

    def test_ipmi_command_fails(self):
        """Test that we skip future checks on failing nodes."""
        self.mock_subprocess_run.return_value.returncode = 1
        waiter = IPMIPowerStateWaiter(self.members, 'on', self.timeout, self.username, self.password)
        self.assertFalse(waiter.member_has_completed('groucho'))


class TestSSHAvailableWaiter(WaiterTestCase):
    """Tests for the sat.cli.bootsys.mgmt_boot_power.SSHAvailableWaiter class"""
    def setUp(self):
        self.mock_ssh_client = patch('sat.cli.bootsys.mgmt_boot_power.SSHClient').start()

        super().setUp()

    def test_pre_wait_action_loads_keys(self):
        """Test the SSH waiter loads system host keys"""
        SSHAvailableWaiter(self.members, self.timeout).pre_wait_action()
        self.mock_ssh_client.return_value.load_system_host_keys.assert_called_once()

    def test_ssh_available(self):
        """Test the SSH waiter detects available nodes"""
        waiter = SSHAvailableWaiter(self.members, self.timeout)
        self.assertTrue(waiter.member_has_completed('groucho'))

    def test_ssh_not_available(self):
        """Test the SSH waiter detects node isn't available due to SSHException"""
        waiter = SSHAvailableWaiter(self.members, self.timeout)
        self.mock_ssh_client.return_value.connect.side_effect = SSHException("SSH doesn't work")
        self.assertFalse(waiter.member_has_completed('groucho'))

    def test_ssh_not_available_no_valid_connection(self):
        """Test the SSH waiter detects node isn't available due to no valid connection"""
        waiter = SSHAvailableWaiter(self.members, self.timeout)
        self.mock_ssh_client.return_value.connect.side_effect = NoValidConnectionsError(
            {('127.0.0.1', '22'): 'Something happened'})
        self.assertFalse(waiter.member_has_completed('groucho'))


def generate_mock_pod(namespace, name, phase):
    """Generate a simple mock V1Pod object."""
    pod = MagicMock()
    pod.metadata.namespace = namespace
    pod.metadata.name = name
    pod.status.phase = phase
    return pod


class TestK8sPodWaiter(WaiterTestCase):
    def setUp(self):
        self.mock_k8s_api = patch('sat.cli.bootsys.mgmt_boot_power.CoreV1Api').start()
        self.mock_load_kube_config = patch('sat.cli.bootsys.mgmt_boot_power.load_kube_config').start()

        self.mocked_pod_dump = {
            'galaxies': {
                'm83': 'Succeeded',
                'milky_way': 'Pending'
            },
            'planets': {
                'jupiter': 'Succeeded',
                'earth': 'Failed'
            }
        }

        mock_recorder = patch('sat.cli.bootsys.mgmt_boot_power.PodStateRecorder').start()
        mock_recorder.get_state_data.return_value = self.mocked_pod_dump

        super().setUp()

    def test_k8s_pod_waiter_completed(self):
        """Test if a k8s pod is considered completed if it is in its previous state"""
        self.mock_k8s_api.return_value.list_pod_for_all_namespaces.return_value.items = [
            generate_mock_pod('galaxies', 'm83', 'Succeeded')
        ]

        waiter = KubernetesPodStatusWaiter(self.timeout)
        self.assertTrue(waiter.member_has_completed(('galaxies', 'm83')))

    def test_k8s_pod_waiter_not_completed(self):
        """Test if a pod in different state from last shutdown is considered not completed"""
        self.mock_k8s_api.return_value.list_pod_for_all_namespaces.return_value.items = [
            generate_mock_pod('galaxies', 'm83', 'Pending')
        ]

        waiter = KubernetesPodStatusWaiter(self.timeout)
        self.assertFalse(waiter.member_has_completed(('galaxies', 'm83')))

    def test_k8s_pod_waiter_new_pod(self):
        """Test if a new pod is considered completed if it succeeded."""
        self.mock_k8s_api.return_value.list_pod_for_all_namespaces.return_value.items = [
            generate_mock_pod('galaxies', 'andromeda', 'Pending')
        ]

        waiter = KubernetesPodStatusWaiter(self.timeout)
        self.assertFalse(waiter.member_has_completed(('galaxies', 'andromeda')))


class TestCephWaiter(WaiterTestCase):
    def setUp(self):
        self.mock_ssh_client = patch('sat.cli.bootsys.mgmt_boot_power.SSHClient').start()

        # TODO: if the Ceph health criteria change, these will need to
        # be modified. (See SAT-559 for further information.)
        self.HEALTH_OK = StringIO('{"health": {"status": "HEALTH_OK"}}')
        self.HEALTH_WARN = StringIO('{"health": {"status": "HEALTH_WARN"}}')

        self.mock_ssh_client.return_value.exec_command.return_value = (None, self.HEALTH_OK, None)

        self.waiter = CephHealthWaiter(10)

        super().setUp()

    def test_ceph_health_connects_ssh(self):
        """Test that CephHealthWaiter connects over SSH properly."""
        self.waiter.has_completed()
        self.mock_ssh_client.return_value.load_system_host_keys.assert_called_once()
        self.mock_ssh_client.return_value.connect.assert_called_once_with(self.waiter.host)
        self.mock_ssh_client.return_value.exec_command.assert_called_once()

    def test_ceph_health_is_ready(self):
        """Test that Ceph readiness is detected."""
        self.assertTrue(self.waiter.has_completed())

    def test_ceph_health_is_not_ready(self):
        """Test that Ceph not being ready is detected."""
        self.mock_ssh_client.return_value.exec_command.return_value = (None, self.HEALTH_WARN, None)
        self.assertFalse(self.waiter.has_completed())

    def test_ceph_health_ssh_broken(self):
        """Test that Ceph health is not complete if there's an SSH problem."""
        self.mock_ssh_client.return_value.exec_command.side_effect = SSHException()
        self.assertFalse(self.waiter.has_completed())

    @patch('sat.cli.bootsys.mgmt_boot_power.json.loads')
    def test_ceph_health_malformed_json(self, mock_json_loads):
        """Test that Ceph health is not complete if Ceph returns malformed JSON."""
        mock_json_loads.side_effect = json.decoder.JSONDecodeError('bad json', 'it is wrong', 0)
        self.assertFalse(self.waiter.has_completed())

    def test_ceph_health_json_bad_schema(self):
        """Test that Ceph health is not complete if the JSON schema is incorrect."""
        self.mock_ssh_client.return_value.exec_command.return_value = (None, StringIO('{"foo": {"bar": "baz"}'), None)
        self.assertFalse(self.waiter.has_completed())


class TestBGPSpineStatusWaiter(WaiterTestCase):
    """Tests for the spine BGP status waiting functionality."""

    INCOMPLETE_OUTPUT = dedent("""\
    PLAY [spines_mtl]
    ****************************************************************************************************

    TASK [Check the BGP status on spine switches commands=['enable', 'show ip bgp summary']]
    ****************************
    Tuesday 14 April 2020  09:23:02 -0500 (0:00:00.056)       0:00:00.056 *********
    fatal: [sw-spine02-mtl]: FAILED! =>
      msg: '[Errno None] Unable to connect to port 22 on 10.1.0.3'
    ok: [sw-spine01-mtl]

    TASK [debug msg={{ result.stdout[1] }}]
    ******************************************************************************
    Tuesday 14 April 2020  09:23:07 -0500 (0:00:05.331)       0:00:05.387 *********
    ok: [sw-spine01-mtl] =>
      msg: |-
        VRF name                  : default
        BGP router identifier     : 10.252.0.1
        local AS number           : 65533
        BGP table version         : 7
        Main routing table version: 7
        IPV4 Prefixes             : 34
        IPV6 Prefixes             : 0
        L2VPN EVPN Prefixes       : 0
    ------------------------------------------------------------------------------------------------------------------
        Neighbor          V    AS           MsgRcvd   MsgSent   TblVer    InQ    OutQ   Up/Down       State/PfxRcd
    ------------------------------------------------------------------------------------------------------------------
        10.252.0.4        4    65533        3         2         7         0      0      Never         IDLE/0
        10.252.0.5        4    65533        14317     16436     7         0      0      4:23:08:24    ESTABLISHED/17
        10.252.0.6        4    65533        14317     16452     7         0      0      4:23:08:24    ESTABLISHED/17

    PLAY RECAP
    ************************************************************************************************************
    sw-spine01-mtl             : ok=2    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
    sw-spine02-mtl             : ok=0    changed=0    unreachable=0    failed=1    skipped=0    rescued=0    ignored=0

    Tuesday 14 April 2020  09:23:08 -0500 (0:00:00.480)       0:00:05.868 *********
    ===============================================================================
    Check the BGP status on spine switches ------------------------------------------------------------------- 5.33s
    debug ---------------------------------------------------------------------------------------------------- 0.48s
    Playbook run took 0 days, 0 hours, 0 minutes, 5 seconds
    """)

    COMPLETE_OUTPUT = dedent("""\
    PLAY [spines_mtl]
    ****************************************************************************************************

    TASK [Check the BGP status on spine switches commands=['enable', 'show ip bgp summary']]
    ****************************
    Tuesday 14 April 2020  09:23:02 -0500 (0:00:00.056)       0:00:00.056 *********
    fatal: [sw-spine02-mtl]: FAILED! =>
      msg: '[Errno None] Unable to connect to port 22 on 10.1.0.3'
    ok: [sw-spine01-mtl]

    TASK [debug msg={{ result.stdout[1] }}]
    ******************************************************************************
    Tuesday 14 April 2020  09:23:07 -0500 (0:00:05.331)       0:00:05.387 *********
    ok: [sw-spine01-mtl] =>
      msg: |-
        VRF name                  : default
        BGP router identifier     : 10.252.0.1
        local AS number           : 65533
        BGP table version         : 7
        Main routing table version: 7
        IPV4 Prefixes             : 34
        IPV6 Prefixes             : 0
        L2VPN EVPN Prefixes       : 0
    ------------------------------------------------------------------------------------------------------------------
        Neighbor          V    AS           MsgRcvd   MsgSent   TblVer    InQ    OutQ   Up/Down       State/PfxRcd
    ------------------------------------------------------------------------------------------------------------------
        10.252.0.4        4    65533        14317     16436     7         0      0      4:23:08:24    ESTABLISHED/17
        10.252.0.5        4    65533        14317     16436     7         0      0      4:23:08:24    ESTABLISHED/17
        10.252.0.6        4    65533        14317     16452     7         0      0      4:23:08:24    ESTABLISHED/17

    PLAY RECAP
    ************************************************************************************************************
    sw-spine01-mtl             : ok=2    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
    sw-spine02-mtl             : ok=0    changed=0    unreachable=0    failed=1    skipped=0    rescued=0    ignored=0

    Tuesday 14 April 2020  09:23:08 -0500 (0:00:00.480)       0:00:05.868 *********
    ===============================================================================
    Check the BGP status on spine switches ------------------------------------------------------------------- 5.33s
    debug ---------------------------------------------------------------------------------------------------- 0.48s
    Playbook run took 0 days, 0 hours, 0 minutes, 5 seconds
    """)

    def setUp(self):
        self.mock_run_playbook = patch('sat.cli.bootsys.mgmt_boot_power.run_ansible_playbook').start()

    def test_spine_bgp_established(self):
        """Test if established BGP peers are recognized."""
        self.assertTrue(BGPSpineStatusWaiter.all_established(self.COMPLETE_OUTPUT))

    def test_spine_bgp_idle(self):
        """Test if idle BGP peers are detected."""
        self.assertFalse(BGPSpineStatusWaiter.all_established(self.INCOMPLETE_OUTPUT))

    def test_get_spine_status(self):
        """Test the get_spine_status helper function."""
        result = 'result of running playbook'
        self.mock_run_playbook.return_value = result

        self.assertEqual(BGPSpineStatusWaiter.get_spine_status(), result)
        self.mock_run_playbook.assert_called_once_with('/opt/cray/crayctl/ansible_framework/main/spine-bgp-status.yml',
                                                       exit_on_err=False)

    @patch('sat.cli.bootsys.mgmt_boot_power.BGPSpineStatusWaiter.get_spine_status')
    def test_completion_successful(self, mock_spine_status):
        """Test the BGP waiter when the BGP peers have been established."""
        mock_spine_status.return_value = self.COMPLETE_OUTPUT
        self.assertTrue(BGPSpineStatusWaiter(10).has_completed())

    def test_completion_when_called_process_error(self):
        """Test the BGP waiter when there's an issue running ansible-playbook."""
        self.mock_run_playbook.return_value = None
        self.assertFalse(BGPSpineStatusWaiter(10).has_completed())

    @patch('sat.cli.bootsys.mgmt_boot_power.BGPSpineStatusWaiter.get_spine_status')
    def test_waiting_for_bgp_completion(self, mock_spine_status):
        """Test waiting for successful BGP peering"""
        mock_spine_status.return_value = self.COMPLETE_OUTPUT
        spine_waiter = BGPSpineStatusWaiter(10)
        self.assertTrue(spine_waiter.wait_for_completion())


class TestHSNBringupWaiter(WaiterTestCase):
    """Test the HSN bringup waiter"""
    def setUp(self):
        self.mock_run_playbook = patch('sat.cli.bootsys.mgmt_boot_power.run_ansible_playbook').start()
        self.mock_session = patch('sat.cli.bootsys.mgmt_boot_power.SATSession').start()
        mock_fabric_client_cls = patch('sat.cli.bootsys.mgmt_boot_power.FabricControllerClient').start()
        self.mock_fabric_client = mock_fabric_client_cls.return_value
        self.mock_fabric_client.get_fabric_edge_ports.return_value = {
            'fabric-ports': [
                'x3000c0r24j4p0',
                'x3000c0r24j4p1',
                'x3000c0r24j8p0',  # exists, does not have status, was present and enabled before shutdown
                'x3000c0r24j8p1'   # exists, is enabled, was not present before shutdown
            ],
            'edge-ports': [
                'x3000c0r24j14p0',
                'x3000c0r24j14p1',
                'x3000c0r24j16p0',  # exists, does not have status, was present and disabled before shutdown
                'x3000c0r24j16p1',  # exists, is disabled, was not present before shutdown
            ]
        }
        self.mock_fabric_client.get_fabric_edge_ports_enabled_status.return_value = {
            'fabric-ports': {
                'x3000c0r24j4p0': True,
                'x3000c0r24j4p1': False,
                # 'x3000c0r24j8p0' intentionally omitted
                'x3000c0r24j8p1': True
            },
            'edge-ports': {
                'x3000c0r24j14p0': True,
                'x3000c0r24j14p1': False,
                # 'x3000c0r24j16p0' intentionally omitted
                'x3000c0r24j16p1': False
            }
        }

        mock_hsn_recorder_cls = patch('sat.cli.bootsys.mgmt_boot_power.HSNStateRecorder').start()
        self.mock_hsn_recorder = mock_hsn_recorder_cls.return_value
        self.mock_hsn_recorder.get_stored_state.return_value = {
            'fabric-ports': {
                'x3000c0r24j4p0': True,
                'x3000c0r24j4p1': False,
                'x3000c0r24j8p0': True
                # 'x3000c0r24j8p1' intentionally omitted
            },
            'edge-ports': {
                'x3000c0r24j14p0': True,
                'x3000c0r24j14p1': True,
                'x3000c0r24j16p0': False
                # 'x3000c0r24j16p1' intentionally omitted
            }
        }

        self.timeout = 1
        self.poll_interval = 1
        self.waiter = HSNBringupWaiter(self.timeout, poll_interval=self.poll_interval)

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_init(self):
        """Test creation of an HSNBringupWaiter."""
        self.assertEqual(self.timeout, self.waiter.timeout)
        self.assertEqual(self.poll_interval, self.waiter.poll_interval)
        self.assertEqual(self.mock_fabric_client, self.waiter.fabric_client)
        self.assertEqual(self.mock_hsn_recorder, self.waiter.hsn_state_recorder)
        self.assertEqual({}, self.waiter.current_hsn_state)

    def test_on_check_action(self):
        """Test that on_check_action calls appropriate fabric client method."""
        self.waiter.on_check_action()
        self.mock_fabric_client.get_fabric_edge_ports_enabled_status.assert_called_once_with()

    def test_stored_hsn_state(self):
        """Test that the stored_hsn_state gets its info from the HSNStateRecorder and caches itself."""
        expected = {'port-set': {'port-xname': 'x5000c0r1j4p0'}}
        self.mock_hsn_recorder.get_stored_state.side_effect = [expected, {}]
        self.assertEqual(expected, self.waiter.stored_hsn_state)
        # It should be cached, so it should not change
        self.assertEqual(expected, self.waiter.stored_hsn_state)
        self.mock_hsn_recorder.get_stored_state.assert_called_once_with()

    def test_stored_hsn_state_error(self):
        """Test stored_hsn_state when the HSNStateRecorder has an error."""
        expected = {}
        self.mock_hsn_recorder.get_stored_state.side_effect = StateError
        self.assertEqual(expected, self.waiter.stored_hsn_state)
        self.mock_hsn_recorder.get_stored_state.assert_called_once_with()

    def test_pre_wait_action(self):
        """Test that the pre_wait_action calls the bringup playbook and sets up members."""
        expected_members = {
            HSNPort('fabric-ports', 'x3000c0r24j4p0'),
            HSNPort('fabric-ports', 'x3000c0r24j4p1'),
            HSNPort('fabric-ports', 'x3000c0r24j8p0'),
            HSNPort('fabric-ports', 'x3000c0r24j8p1'),
            HSNPort('edge-ports', 'x3000c0r24j14p0'),
            HSNPort('edge-ports', 'x3000c0r24j14p1'),
            HSNPort('edge-ports', 'x3000c0r24j16p0'),
            HSNPort('edge-ports', 'x3000c0r24j16p1')
        }
        self.waiter.pre_wait_action()

        self.mock_run_playbook.assert_called_once_with(
            '/opt/cray/crayctl/ansible_framework/main/ncmp_hsn_bringup.yaml',
            exit_on_err=False
        )
        self.assertEqual(expected_members, self.waiter.members)

    def test_ports_basic_enabled(self):
        """Test that enabled ports present before shutdown have completed."""
        ports = [
            HSNPort('fabric-ports', 'x3000c0r24j4p0'),
            HSNPort('edge-ports', 'x3000c0r24j14p0')
        ]
        # Have to call this to get self.waiter.current_hsn_state updated
        self.waiter.on_check_action()
        for port in ports:
            self.assertTrue(self.waiter.member_has_completed(port))

    def test_port_disabled_before_and_after(self):
        """Test that a disabled port that was disabled before shutdown is complete."""
        self.waiter.on_check_action()
        self.assertTrue(self.waiter.member_has_completed(HSNPort('fabric-ports', 'x3000c0r24j4p1')))

    def test_port_enabled_before_disabled_after(self):
        """Test that a disabled port that was enabled before shutdown is not complete."""
        self.waiter.on_check_action()
        self.assertFalse(self.waiter.member_has_completed(HSNPort('edge-ports', 'x3000c0r24j14p1')))

    def test_port_enabled_before_missing_after(self):
        """Test that a port that was enabled before shutdown, now missing status is not complete."""
        self.waiter.on_check_action()
        self.assertFalse(self.waiter.member_has_completed(HSNPort('fabric-ports', 'x3000c0r24j8p0')))

    def test_port_missing_before_enabled_after(self):
        """Test that a port that was missing before shutdown, enabled after is complete."""
        self.waiter.on_check_action()
        self.assertTrue(self.waiter.member_has_completed(HSNPort('fabric-ports', 'x3000c0r24j8p1')))

    def test_port_disabled_before_missing_after(self):
        """Test that a port that was disabled before shutdown, missing after is not complete."""
        self.waiter.on_check_action()
        self.assertFalse(self.waiter.member_has_completed(HSNPort('edge-ports', 'x3000c0r24j16p0')))

    def test_port_missing_before_disabled_after(self):
        """Test that a port that was missing before shutdown, disabled after is not complete."""
        self.waiter.on_check_action()
        self.assertFalse(self.waiter.member_has_completed(HSNPort('edge-ports', 'x3000c0r24j16p1')))


class TestRestartCephServices(ExtendedTestCase):
    """Test restart_ceph_services()"""

    def setUp(self):
        self.mock_ssh_client_cls = patch('sat.cli.bootsys.mgmt_boot_power.SSHClient').start()
        self.mock_ssh_client = self.mock_ssh_client_cls.return_value
        self.mock_connect = self.mock_ssh_client.connect
        self.mock_load_system_host_keys = self.mock_ssh_client.load_system_host_keys
        self.mock_exec_command = self.mock_ssh_client.exec_command
        self.mock_stdin, self.mock_stdout, self.mock_stderr = Mock(), Mock(), Mock()
        self.mock_stdin.channel.recv_exit_status.return_value = 0
        self.mock_stdout.channel.recv_exit_status.return_value = 0
        self.mock_stderr.channel.recv_exit_status.return_value = 0
        self.mock_exec_command.return_value = (self.mock_stdin, self.mock_stdout, self.mock_stderr)

        self.mock_get_groups = patch('sat.cli.bootsys.mgmt_boot_power.get_groups').start()
        self.hosts = ['ncn-s001', 'ncn-s002', 'ncn-s003']
        self.mock_get_groups.return_value = self.hosts

        self.services_to_restart = ['ceph-mon.target', 'ceph-mgr.target', 'ceph-mds.target']

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def assert_client(self):
        """Helper for test cases to assert that the SSH client was initialized correctly"""
        self.mock_get_groups.assert_called_once_with(['storage'])
        self.mock_ssh_client_cls.assert_called_once()
        self.mock_load_system_host_keys.assert_called_once()

    def test_basic_restart(self):
        """Test a basic invocation of restart_ceph_services"""
        restart_ceph_services()
        self.assert_client()
        self.mock_connect.assert_has_calls([call(host) for host in self.hosts])
        self.mock_exec_command.assert_has_calls([call(f'systemctl restart {service}')
                                                 for service in self.services_to_restart] * len(self.hosts))

    def test_connect_failed(self):
        """Test when connecting to a host fails"""
        self.mock_connect.side_effect = SSHException('the system is down')
        with self.assertRaises(SystemExit):
            with self.assertLogs(level=logging.ERROR) as cm:
                restart_ceph_services()

        self.assert_client()
        self.mock_connect.assert_called_once_with(self.hosts[0])
        self.assert_in_element(f'Connecting to {self.hosts[0]} failed.  Error: the system is down', cm.output)

    def test_command_failed(self):
        """Test when running a command fails"""
        self.mock_exec_command.side_effect = SSHException('the system crashed')
        with self.assertRaises(SystemExit):
            with self.assertLogs(level=logging.ERROR) as cm:
                restart_ceph_services()

        self.assert_client()
        self.mock_connect.assert_called_once_with(self.hosts[0])
        self.mock_exec_command.assert_called_once_with(f'systemctl restart ceph-mon.target')
        self.assert_in_element(f'Command "systemctl restart ceph-mon.target" failed.  Host: {self.hosts[0]}.  '
                               f'Error: the system crashed', cm.output)

    def test_command_exit_nonzero(self):
        """Test when running a command completes but returns a nonzero exit code"""
        self.mock_stdout.read.return_value = ''
        self.mock_stderr.read.return_value = 'command failed!'
        # stdin/stderr/stdout all have recv_exit_status() set on a nonzero return
        self.mock_stdin.chanel.recv_exit_status.return_value = 1
        self.mock_stdout.channel.recv_exit_status.return_value = 1
        self.mock_stderr.channel.recv_exit_status.return_value = 1

        with self.assertRaises(SystemExit):
            with self.assertLogs(level=logging.ERROR) as cm:
                restart_ceph_services()

        self.assert_client()
        self.mock_connect.assert_called_once_with(self.hosts[0])
        self.mock_exec_command.assert_called_once_with('systemctl restart ceph-mon.target')
        self.assert_in_element(f'Command "systemctl restart ceph-mon.target" failed.  Host: {self.hosts[0]}.  '
                               f'Stderr: command failed!', cm.output)
