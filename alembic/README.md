# Alembic Database Migrations

This directory contains Alembic configuration and migration files for database schema management.
Alembic is used to handle database migrations, allowing for version control of database schema changes.
The `versions/` folder contains individual migration scripts that modify the database structure over time.
Each migration file represents a specific change to the database schema with upgrade and downgrade functions.
This ensures consistent database state across different environments and deployment stages.