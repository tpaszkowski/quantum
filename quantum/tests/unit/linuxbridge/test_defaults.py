# Copyright (c) 2012 OpenStack Foundation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo.config import cfg

from quantum.plugins.linuxbridge.common import config  # noqa
from quantum.tests import base


class ConfigurationTest(base.BaseTestCase):

    def test_defaults(self):
        self.assertEqual(2,
                         cfg.CONF.AGENT.polling_interval)
        self.assertEqual('sudo',
                         cfg.CONF.AGENT.root_helper)
        self.assertEqual('local',
                         cfg.CONF.VLANS.tenant_network_type)
        self.assertEqual(0,
                         len(cfg.CONF.VLANS.network_vlan_ranges))
        self.assertEqual(0,
                         len(cfg.CONF.LINUX_BRIDGE.
                             physical_interface_mappings))
        self.assertIsNone(cfg.CONF.VXLAN.vxlan_ttl)
        self.assertEqual('239.1.1.1', cfg.CONF.VXLAN.vxlan_group)
        self.assertIsNone(cfg.CONF.VXLAN.vxlan_tos)
        self.assertEqual(0, len(cfg.CONF.VXLAN.vxlan_port))
        self.assertIsNone(cfg.CONF.VXLAN.vxlan_local_ip)
