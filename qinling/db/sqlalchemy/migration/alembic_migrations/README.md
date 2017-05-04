The migrations in `alembic_migrations/versions` contain the changes needed to migrate
between Qinling database revisions. A migration occurs by executing a script that
details the changes needed to upgrade the database. The migration scripts
are ordered so that multiple scripts can run sequentially. The scripts are executed by
Qinling's migration wrapper which uses the Alembic library to manage the migration. Qinling
supports migration from Pike or later.

You can upgrade to the latest database version via:
```
qinling-db-manage --config-file /path/to/qinling.conf upgrade head
```

To check the current database version:
```
qinling-db-manage --config-file /path/to/qinling.conf current
```

To create a script to run the migration offline:
```
qinling-db-manage --config-file /path/to/qinling.conf upgrade head --sql
```

To run the offline migration between specific migration versions:
```
qinling-db-manage --config-file /path/to/qinling.conf upgrade <start version>:<end version> --sql
```

Upgrade the database incrementally:
```
qinling-db-manage --config-file /path/to/qinling.conf upgrade --delta <# of revs>
```

Or, upgrade the database to one newer revision:
```
qinling-db-manage --config-file /path/to/qinling.conf upgrade +1
```

Create new revision:
```
qinling-db-manage --config-file /path/to/qinling.conf revision -m "description of revision" --autogenerate
```

Create a blank file:
```
qinling-db-manage --config-file /path/to/qinling.conf revision -m "description of revision"
```

This command does not perform any migrations, it only sets the revision.
Revision may be any existing revision. Use this command carefully.
```
qinling-db-manage --config-file /path/to/qinling.conf stamp <revision>
```

To verify that the timeline does branch, you can run this command:
```
qinling-db-manage --config-file /path/to/qinling.conf check_migration
```

If the migration path has branch, you can find the branch point via:
```
qinling-db-manage --config-file /path/to/qinling.conf history