# Database DevOps Policies

## Package: `db_sql`
## Root path: `input.dbInstance`, `input.dbSchema`, `input.sqlStatements`
## Valid actions: `onsave`

## Input Schema

```
input.dbInstance.identifier
input.dbInstance.name
input.dbInstance.type                        # "jdbc:sqlserver", "jdbc:mysql", "jdbc:postgresql", "jdbc:oracle:thin"
input.dbInstance.dbConnectionUrl
input.dbInstance.tags                        # object { "key": "value" }

input.dbSchema.identifier
input.dbSchema.name

input.sqlStatements[]                        # array of SQL statement strings
```

## Example 1: Block DROP TABLE statements

**Scenario:** Prevent dropping tables across all supported database types.

```rego
package db_sql

jdbc_databases := [
  "jdbc:sqlserver",
  "jdbc:mysql",
  "jdbc:postgresql",
  "jdbc:oracle:thin"
]

deny[msg] {
  db_type := input.dbInstance.type
  array_contains(jdbc_databases, db_type)
  statement := input.sqlStatements[_]
  contains(lower(statement), "drop")
  msg := sprintf("Dropping of table is not allowed. Statement: '%s'", [statement])
}

array_contains(arr, elem) {
  arr[_] = elem
}
```

## Example 2: Enforce table name length

**Scenario:** Table names in CREATE TABLE statements must not exceed 10 characters.

```rego
package db_sql

deny[msg] {
  statement := input.sqlStatements[_]
  regex.match("(?i)create\\s+table", statement)
  table_name := extract_table_name(statement)
  count(table_name) > 10
  msg := sprintf("Table name '%s' exceeds maximum length of 10 characters", [table_name])
}

extract_table_name(statement) = name {
  regex.match("(?i)create\\s+table\\s+\\w+\\.\\w+", statement)
  parts := regex.find_all_string_submatch_n("(?i)create\\s+table\\s+\\w+\\.(\\w+)", statement, 1)
  name := parts[0][1]
}

extract_table_name(statement) = name {
  not regex.match("(?i)create\\s+table\\s+\\w+\\.\\w+", statement)
  parts := regex.find_all_string_submatch_n("(?i)create\\s+table\\s+(\\w+)", statement, 1)
  name := parts[0][1]
}
```

## Example 3: Enforce schema name length

**Scenario:** Schema names in CREATE SCHEMA statements must not exceed 30 characters.

```rego
package db_sql

deny[msg] {
  statement := input.sqlStatements[_]
  regex.match("(?i)create\\s+schema", statement)
  parts := regex.find_all_string_submatch_n("(?i)create\\s+schema\\s+(\\w+)", statement, 1)
  schema_name := parts[0][1]
  count(schema_name) > 30
  msg := sprintf("Schema name '%s' exceeds maximum length of 30 characters", [schema_name])
}
```

## Example 4: Block system table access

**Scenario:** Prevent direct access to system tables and catalog views.

```rego
package db_sql

system_patterns := [
  "sys.",
  "information_schema.",
  "pg_catalog.",
  "sysobjects",
  "syscolumns",
  "sysusers"
]

deny[msg] {
  statement := input.sqlStatements[_]
  pattern := system_patterns[_]
  contains(lower(statement), pattern)
  msg := sprintf("Direct access to system tables is not permitted. Found '%s' in statement.", [pattern])
}
```

## Example 5: Limit transaction size

**Scenario:** Prevent large transactions by limiting the number of SQL statements to 50.

```rego
package db_sql

max_statements := 50

deny[msg] {
  count(input.sqlStatements) > max_statements
  msg := sprintf("Transaction contains %d statements, exceeding the maximum of %d", [count(input.sqlStatements), max_statements])
}
```

## Example 6: Database-specific restrictions

**Scenario:** Enforce database-type-specific governance rules — block dangerous DDL operations per database engine.

```rego
package db_sql

# Oracle: block user/role creation and profile/tablespace modifications
deny[msg] {
  contains(input.dbInstance.type, "oracle")
  statement := input.sqlStatements[_]
  regex.match("(?i)(create|alter|drop)\\s+(user|role|profile|tablespace)", lower(statement))
  msg := sprintf("Oracle admin DDL operations are not allowed: '%s'", [statement])
}

# SQL Server: block system stored procedures and user management
deny[msg] {
  contains(input.dbInstance.type, "sqlserver")
  statement := input.sqlStatements[_]
  regex.match("(?i)(sp_addrolemember|sp_droprolemember|sp_addlogin|sp_droplogin)", lower(statement))
  msg := sprintf("SQL Server system stored procedures are not allowed: '%s'", [statement])
}

# All databases: block granting permissions to PUBLIC role
deny[msg] {
  statement := input.sqlStatements[_]
  regex.match("(?i)(grant|revoke).*\\bpublic\\b", lower(statement))
  msg := sprintf("Granting/revoking permissions to PUBLIC role is not allowed: '%s'", [statement])
}
```

## Sample JSON

```json
{
  "dbInstance": {
    "dbConnectionUrl": "jdbc:sqlserver://myhost:1433;databaseName=mydb",
    "identifier": "my_db_instance",
    "name": "My Database",
    "tags": { "team": "platform", "env": "production" },
    "type": "jdbc:sqlserver"
  },
  "dbSchema": {
    "identifier": "my_schema",
    "name": "dbo"
  },
  "sqlStatements": [
    "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))",
    "ALTER TABLE users ADD email VARCHAR(255)"
  ]
}
```
