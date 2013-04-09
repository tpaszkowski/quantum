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


from sqlalchemy.orm import exc

from quantum.common import exceptions as q_exc
import quantum.db.api as db
from quantum.db import models_v2
from quantum.db import securitygroups_db as sg_db
from quantum import manager
from quantum.openstack.common import log as logging
from quantum.plugins.linuxbridge.common import config  # noqa
from quantum.plugins.linuxbridge.common import constants
from quantum.plugins.linuxbridge.db import l2network_models_v2

LOG = logging.getLogger(__name__)


def initialize():
    db.configure_db()


def sync_network_states(tenant_network_type, network_vlan_ranges):
    """Synchronize network_states table with current configured VLAN ranges."""

    session = db.get_session()
    with session.begin():
        # get existing allocations for all physical networks
        states = (session.query(l2network_models_v2.NetworkState).
                  all())
        allocations = build_network_allocations(states)
        # sync tenant_network_type networks
        if not tenant_network_type in allocations:
            allocations[tenant_network_type] = dict()
        sync_tenant_network_states(session,
                                   allocations[tenant_network_type],
                                   tenant_network_type,
                                   network_vlan_ranges)
        del(allocations[tenant_network_type])
        # delete all other unallocated networks
        for network_type in allocations.iterkeys():
            delete_unallocated_network_states(session,
                                              allocations[network_type])


def build_network_allocations(states):
    allocations = dict()
    for state in states:
        if state.network_type not in allocations:
            allocations[state.network_type] = dict()
        network_allocations = allocations[state.network_type]
        if state.physical_network not in network_allocations:
            network_allocations[state.physical_network] = set()
        network_allocations[state.physical_network].add(state)
    return allocations


def sync_tenant_network_states(session, allocations, network_type,
                               network_vlan_ranges):
    # process vlan ranges for each configured physical network
    for physical_network, vlan_ranges in network_vlan_ranges.iteritems():
        # determine current configured allocatable vlans for this
        # physical network
        vlan_ids = set()
        for vlan_range in vlan_ranges:
            vlan_ids |= set(xrange(vlan_range[0], vlan_range[1] + 1))

        # remove from table unallocated vlans not currently allocatable
        if physical_network in allocations:
            for state in allocations[physical_network]:
                try:
                    # see if vlan is allocatable
                    vlan_ids.remove(state.vlan_id)
                except KeyError:
                    # it's not allocatable, so check if its allocated
                    if not state.allocated:
                        # it's not, so remove it from table
                        delete_network_state(session, state)
            del allocations[physical_network]
        # add missing allocatable vlans to table
        for vlan_id in sorted(vlan_ids):
            state = l2network_models_v2.NetworkState(network_type,
                                                     physical_network, vlan_id)
            session.add(state)

    # delete unused physical_networks allocations
    delete_unallocated_network_states(session, allocations)


def delete_unallocated_network_states(session, allocations):
    # remove from table unallocated vlans
    for states in allocations.itervalues():
        for state in states:
            if not state.allocated:
                delete_network_state(session, state)


def delete_network_state(session, state):
    LOG.debug(_("Removing vlan %(vlan_id)s on physical network "
                "%(physical_network)s for network type %(network_type) from "
                " pool"),
              {'vlan_id': state.vlan_id,
               'physical_network': state.physical_network,
               'network_type': state.network_type})
    session.delete(state)


def get_network_state(network_type, physical_network, vlan_id):
    """Get state of specified network."""

    session = db.get_session()
    try:
        state = (session.query(l2network_models_v2.NetworkState).
                 filter_by(network_type=network_type,
                           physical_network=physical_network,
                           vlan_id=vlan_id).
                 one())
        return state
    except exc.NoResultFound:
        return None


def reserve_network(session, network_type):
    with session.begin(subtransactions=True):
        state = (session.query(l2network_models_v2.NetworkState).
                 filter_by(network_type=network_type, allocated=False).
                 with_lockmode('update').
                 first())
        if not state:
            raise q_exc.NoNetworkAvailable()
        LOG.debug(_("Reserving vlan %(vlan_id)s on physical network "
                    "%(physical_network)s for network type %(network_type) "
                    "from pool"),
                  {'vlan_id': state.vlan_id,
                   'physical_network': state.physical_network,
                   'network_type': state.network_type})
        state.allocated = True
    return (state.physical_network, state.vlan_id)


def reserve_specific_network(session, network_type, physical_network, vlan_id):
    with session.begin(subtransactions=True):
        try:
            state_q = (session.query(l2network_models_v2.NetworkState).
                       filter_by(vlan_id=vlan_id, network_type=network_type))
            if network_type != constants.TYPE_VXLAN:
            # for non VXLAN networks vlan numbering if per physical_network
                state_q = state_q.filter_by(physical_network=physical_network)
            state = state_q.with_lockmode('update').one()
            if state.allocated:
                if vlan_id == constants.FLAT_VLAN_ID:
                    raise q_exc.FlatNetworkInUse(
                        physical_network=physical_network)
                else:
                    raise q_exc.VlanIdInUse(vlan_id=vlan_id,
                                            physical_network=physical_network)
            LOG.debug(_("Reserving specific vlan %(vlan_id)s on physical "
                        "network %(physical_network)s for network type "
                        "%(network_type) from pool"),
                      dict(vlan_id=vlan_id, physical_network=physical_network,
                           network_type=network_type))
            state.allocated = True
        except exc.NoResultFound:
            LOG.debug(_("Reserving specific vlan %(vlan_id)s on physical "
                        "network %(physical_network)s for network_type "
                        "%(network_type) outside pool"),
                      dict(vlan_id=vlan_id, physical_network=physical_network,
                           network_type=network_type))
            state = l2network_models_v2.NetworkState(network_type,
                                                     physical_network, vlan_id)
            state.allocated = True
            session.add(state)


def release_network(session, network_type, physical_network, vlan_id,
                    network_vlan_ranges):
    with session.begin(subtransactions=True):
        try:
            state = (session.query(l2network_models_v2.NetworkState).
                     filter_by(physical_network=physical_network,
                               network_type=network_type,
                               vlan_id=vlan_id).
                     with_lockmode('update').
                     one())
            state.allocated = False
            inside = False
            if not network_vlan_ranges:
                # just delete network state
                LOG.debug(_("Releasing vlan %(vlan_id)s on physical network "
                            "%(physical_network)s for network type "
                            "%(network_type)s"),
                          dict(vlan_id=vlan_id,
                               physical_network=physical_network,
                               network_type=network_type))
                session.delete(state)
                return
            for vlan_range in network_vlan_ranges.get(physical_network, []):
                if vlan_id >= vlan_range[0] and vlan_id <= vlan_range[1]:
                    inside = True
                    break
            if inside:
                LOG.debug(_("Releasing vlan %(vlan_id)s on physical network "
                            "%(physical_network)s for network type "
                            "%(network_type)s to pool"),
                          dict(vlan_id=vlan_id,
                               physical_network=physical_network,
                               network_type=network_type))
            else:
                LOG.debug(_("Releasing vlan %(vlan_id)s on physical network "
                            "%(physical_network)s for network type "
                            "%(network_type)s outside pool"),
                          dict(vlan_id=vlan_id,
                               physical_network=physical_network,
                               network_type=network_type))
                session.delete(state)
        except exc.NoResultFound:
            LOG.warning(_("vlan_id %(vlan_id)s on physical network "
                          "%(physical_network)s for network type "
                          "%(network_type)s not found"),
                        dict(vlan_id=vlan_id,
                             physical_network=physical_network,
                             network_type=network_type))


def add_network_binding(session, network_id, network_type, physical_network,
                        vlan_id):
    with session.begin(subtransactions=True):
        binding = l2network_models_v2.NetworkBinding(network_id, network_type,
                                                     physical_network, vlan_id)
        session.add(binding)


def get_network_binding(session, network_id):
    try:
        binding = (session.query(l2network_models_v2.NetworkBinding).
                   filter_by(network_id=network_id).
                   one())
        return binding
    except exc.NoResultFound:
        return


def get_port_from_device(device):
    """Get port from database."""
    LOG.debug(_("get_port_from_device() called"))
    session = db.get_session()
    sg_binding_port = sg_db.SecurityGroupPortBinding.port_id

    query = session.query(models_v2.Port,
                          sg_db.SecurityGroupPortBinding.security_group_id)
    query = query.outerjoin(sg_db.SecurityGroupPortBinding,
                            models_v2.Port.id == sg_binding_port)
    query = query.filter(models_v2.Port.id.startswith(device))
    port_and_sgs = query.all()
    if not port_and_sgs:
        return
    port = port_and_sgs[0][0]
    plugin = manager.QuantumManager.get_plugin()
    port_dict = plugin._make_port_dict(port)
    port_dict['security_groups'] = []
    for port_in_db, sg_id in port_and_sgs:
        if sg_id:
            port_dict['security_groups'].append(sg_id)
    port_dict['security_group_rules'] = []
    port_dict['security_group_source_groups'] = []
    port_dict['fixed_ips'] = [ip['ip_address']
                              for ip in port['fixed_ips']]
    return port_dict


def set_port_status(port_id, status):
    """Set the port status."""
    LOG.debug(_("set_port_status as %s called"), status)
    session = db.get_session()
    try:
        port = session.query(models_v2.Port).filter_by(id=port_id).one()
        port['status'] = status
        session.merge(port)
        session.flush()
    except exc.NoResultFound:
        raise q_exc.PortNotFound(port_id=port_id)
