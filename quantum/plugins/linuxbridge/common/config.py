# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 Cisco Systems, Inc.  All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Sumit Naiksatam, Cisco Systems, Inc.
# @author: Rohit Agarwalla, Cisco Systems, Inc.

from oslo.config import cfg

from quantum.agent.common import config
from quantum import scheduler

DEFAULT_VLAN_RANGES = []
DEFAULT_VNI_RANGES = []
DEFAULT_INTERFACE_MAPPINGS = []
DEFAULT_VXLAN_TTL = None
DEFAULT_VXLAN_GROUP = '239.1.1.1'
DEFAULT_VXLAN_TOS = None
DEFAULT_VXLAN_PORT = []
DEFAULT_VXLAN_LOCAL_IP = None

vlan_opts = [
    cfg.StrOpt('tenant_network_type', default='local',
               help=_("Network type for tenant networks "
                      "(local, vlan, vxlan or none)")),
    cfg.ListOpt('network_vlan_ranges',
                default=DEFAULT_VLAN_RANGES,
                help=_("List of <physical_network>:<vlan_min>:<vlan_max> "
                       "or <physical_network>")),
]

bridge_opts = [
    cfg.ListOpt('physical_interface_mappings',
                default=DEFAULT_INTERFACE_MAPPINGS,
                help=_("List of <physical_network>:<physical_interface>")),
    cfg.StrOpt('tenant_network_type', default='local',
               help=_("Network type for tenant networks "
                      "(local, vlan, vxlan or none)")),
]

agent_opts = [
    cfg.IntOpt('polling_interval', default=2,
               help=_("The number of seconds the agent will wait between "
                      "polling for local device changes.")),
]

vxlan_opts = [
    cfg.ListOpt('network_vni_ranges',
                default=DEFAULT_VLAN_RANGES,
                help=_("List of <physical_network>:<vni_min>:"
                       "<vni_max> ")),
    cfg.IntOpt('vxlan_ttl', default=DEFAULT_VXLAN_TTL,
               help=_("TTL for vxlan interface protocol packets.")),
    cfg.StrOpt('vxlan_group', default=DEFAULT_VXLAN_GROUP,
               help=_("Multicast group for vxlan interface.")),
    cfg.IntOpt('vxlan_tos', default=DEFAULT_VXLAN_TOS,
               help=_("TOS for vxlan interface protocol packets.")),
    cfg.ListOpt('vxlan_port', default=DEFAULT_VXLAN_PORT,
                help=_("Port range for vxlan interface protocol packets "
                       "(min,max).")),
    cfg.StrOpt('vxlan_local_ip', default=DEFAULT_VXLAN_LOCAL_IP,
               help=_("Local ip for vxlan interface protocol packets.")),
]


cfg.CONF.register_opts(vlan_opts, "VLANS")
cfg.CONF.register_opts(bridge_opts, "LINUX_BRIDGE")
cfg.CONF.register_opts(agent_opts, "AGENT")
cfg.CONF.register_opts(vxlan_opts, "VXLAN")
cfg.CONF.register_opts(scheduler.AGENTS_SCHEDULER_OPTS)
config.register_agent_state_opts_helper(cfg.CONF)
config.register_root_helper(cfg.CONF)
