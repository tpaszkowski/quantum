# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013 OpenStack Foundation
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

"""add_network_type_linuxbridge

This retroactively provides migration support for
https://review.openstack.org/#/c//26516/

Revision ID: 43d0147adfd9
Revises: grizzly
Create Date: 2013-04-10 10:44:24.007878

"""

# revision identifiers, used by Alembic.
revision = '43d0147adfd9'
down_revision = 'grizzly'

# Change to ['*'] if this migration applies to all plugins

migration_for_plugins = [
    'quantum.plugins.linuxbridge.lb_quantum_plugin.LinuxBridgePluginV2'
]

from alembic import op
import sqlalchemy as sa
from sqlalchemy import schema as sa_schema
from sqlalchemy.types import NULLTYPE


from quantum.db import migration


# taken from alembic 0.5
def _primary_key_constraint(name, table_name, cols, schema=None):
    m = sa_schema.MetaData()
    columns = [sa_schema.Column(n, NULLTYPE) for n in cols]
    t1 = sa_schema.Table(table_name, m, *columns, schema=schema)
    p = sa_schema.PrimaryKeyConstraint(*columns, name=name)
    t1.append_constraint(p)
    op.get_context().impl.add_constraint(p)


def upgrade(active_plugin=None, options=None):
    if not migration.should_run(active_plugin, migration_for_plugins):
        return

    op.drop_constraint('primary', 'network_states', type='primary')
    op.add_column('network_bindings',
                  sa.Column('network_type', sa.String(32), nullable=False))
    op.add_column('network_states',
                  sa.Column('network_type', sa.String(32), nullable=False))
    op.execute("UPDATE network_bindings SET network_type = 'local' WHERE "
               "vlan_id = -2")
    op.execute("UPDATE network_bindings SET network_type = 'flat' WHERE "
               "vlan_id = -1")
    op.execute("UPDATE network_bindings SET network_type = 'vlan' WHERE "
               "vlan_id > 0")
    op.execute("UPDATE network_states SET network_type = 'local' WHERE "
               "vlan_id = -2")
    op.execute("UPDATE network_states SET network_type = 'flat' WHERE "
               "vlan_id = -1")
    op.execute("UPDATE network_states SET network_type = 'vlan' WHERE "
               "vlan_id > 0")
    # dirty hack for older alembic versions (<0.5)
    _primary_key_constraint('p_key', 'network_states',
                            ['physical_network', 'vlan_id', 'network_type'])


def downgrade(active_plugin=None, options=None):
    if not migration.should_run(active_plugin, migration_for_plugins):
        return

    op.drop_column('network_bindings', 'network_type')
    op.drop_column('network_states', 'network_type')