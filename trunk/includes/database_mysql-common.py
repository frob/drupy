# Id: database.mysql-common.inc,v 1.19 2008/04/14 17:48:33 dries Exp $
#
# @file
# Functions shared between mysql and mysqli database engines.
#

require_once( './lib/drupy/DrupyMySQL.py' )


#
# Runs a basic query in the active database.
#
# User-supplied arguments to the query should be passed in as separate
# parameters so that they can be properly escaped to avoid SQL injection
# attacks.
#
# @param query
#   A string containing an SQL query.
# @param ...
#   A variable number of arguments which are substituted into the query
#   using printf() syntax. Instead of a variable number of query arguments,
#   you may also pass a single array containing the query arguments.
#
#   Valid %-modifiers are: %s, %d, %f, %b (binary data, do not enclose
#   in '') and %%.
#
#   NOTE: using this syntax will cast None and False values to decimal 0,
#   and True values to decimal 1.
#
# @return
#   A database query result resource, or False if the query was not
#   executed correctly.
#
def db_query(query):
  args = func_get_args()
  array_shift(args)
  query = db_prefix_tables(query)
  if (isset(args, 0) and is_array(args, 0)): # 'All arguments in one array' syntax
    args = args[0]
  _db_query_callback(args, True)
  query = preg_replace_callback(DB_QUERY_REGEXP, '_db_query_callback', query)
  return _db_query(query)



#
# @ingroup schemaapi
# @{
#
#
# Generate SQL to create a new table from a Drupal schema definition.
#
# @param name
#   The name of the table to create.
# @param table
#   A Schema API table definition array.
# @return
#   An array of SQL statements to create the table.
#
def db_create_table_sql(name, table):
  if (empty(table['mysql_suffix'])):
    table['mysql_suffix'] = "/*not 40100 DEFAULT CHARACTER SET UTF8 */"
  sql = "CREATE TABLE {" +  name  + "} (\n"
  # Add the SQL statement for each field.
  for field_name,field in table['fields'].items():
    sql += _db_create_field_sql(field_name, _db_process_field(field)) +  ", \n"
  # Process keys & indexes.
  keys = _db_create_keys_sql(table)
  if (count(keys)):
    sql += implode(", \n", keys) +  ", \n"
  # Remove the last comma and space.
  sql = substr(sql, 0, -3) +  "\n) "
  sql += table['mysql_suffix']
  return array(sql)




def _db_create_keys_sql(spec):
  keys = {}
  if (not empty(spec['primary key'])):
    keys.append( 'PRIMARY KEY (' +  _db_create_key_sql(spec['primary key'])  + ')' )
  if (not empty(spec['unique keys'])):
    for key,fields in spec['unique keys'].items():
      keys.append( 'UNIQUE KEY ' +  key  + ' (' + _db_create_key_sql(fields) + ')' )
  if (not empty(spec['indexes'])):
    for index,fields in spec['indexes'].items():
      keys.append( 'INDEX ' +  index  + ' (' + _db_create_key_sql(fields) + ')' )
  return keys




def _db_create_key_sql(fields):
  ret = []
  for field in fields:
    if (is_array(field)):
      ret.append( field[0] +  '('  + field[1] + ')' )
    else:
      ret.append( field )
  return implode(', ', ret)



#
# Set database-engine specific properties for a field.
#
# @param field
#   A field description array, as specified in the schema documentation.
#
def _db_process_field(field):
  if (not isset(field, 'size')):
    field['size'] = 'normal'
  # Set the correct database-engine specific datatype.
  if (not isset(field, 'mysql_type')):
    _map = db_type_map()
    field['mysql_type'] = _map[field['type'] +  ':'  + field['size']]
  if (field['type'] == 'serial'):
    field['auto_increment'] = True
  return field



#
# Create an SQL string for a field to be used in table creation or alteration.
#
# Before passing a field out of a schema definition into this function it has
# to be processed by _db_process_field().
#
# @param name
#    Name of the field.
# @param spec
#    The field specification, as per the schema data structure format.
#
def _db_create_field_sql(name, spec):
  sql = "`" +  name  + "` " . spec['mysql_type']
  if (isset(spec, 'length')):
    sql += '(' +  spec['length']  + ')'
  elif (isset(spec, 'precision') and isset(spec, 'scale')):
    sql += '(' +  spec['precision']  + ', ' + spec['scale'] + ')'
  if (not empty(spec['unsigned'])):
    sql += ' unsigned'
  if (not empty(spec['not None'])):
    sql += ' NOT None'
  if (not empty(spec['auto_increment'])):
    sql += ' auto_increment'
  if (isset(spec, 'default')):
    if (is_string(spec['default'])):
      spec['default'] = "'" +  spec['default']  + "'"
    sql += ' DEFAULT ' +  spec['default']
  if (empty(spec['not None']) and not isset(spec, 'default')):
    sql += ' DEFAULT None'
  return sql





#
# This maps a generic data type in combination with its data size
# to the engine-specific data type.
#
def db_type_map():
  # Put :normal last so it gets preserved by array_flip.  This makes
  # it much easier for modules (such as schema.module) to map
  # database types back into schema types.
  _map = {
    'varchar:normal'  : 'VARCHAR',
    'char:normal'     : 'CHAR',
    'text:tiny'       : 'TINYTEXT',
    'text:small'      : 'TINYTEXT',
    'text:medium'     : 'MEDIUMTEXT',
    'text:big'        : 'LONGTEXT',
    'text:normal'     : 'TEXT',
    'serial:tiny'     : 'TINYINT',
    'serial:small'    : 'SMALLINT',
    'serial:medium'   : 'MEDIUMINT',
    'serial:big'      : 'BIGINT',
    'serial:normal'   : 'INT',
    'int:tiny'        : 'TINYINT',
    'int:small'       : 'SMALLINT',
    'int:medium'      : 'MEDIUMINT',
    'int:big'         : 'BIGINT',
    'int:normal'      : 'INT',
    'float:tiny'      : 'FLOAT',
    'float:small'     : 'FLOAT',
    'float:medium'    : 'FLOAT',
    'float:big'       : 'DOUBLE',
    'float:normal'    : 'FLOAT',
    'numeric:normal'  : 'DECIMAL',
    'blob:big'        : 'LONGBLOB',
    'blob:normal'     : 'BLOB',
    'datetime:normal' : 'DATETIME'
  }
  return _map



#
# Rename a table.
#
# @param ret
#   Array to which query results will be added.
# @param table
#   The table to be renamed.
# @param new_name
#   The new name for the table.
#
def db_rename_table(ret, table, new_name):
  DrupyHelper.Reference.check(ref)
  ret.val.append( update_sql('ALTER TABLE {' +  table  + '} RENAME TO {' + new_name + '}') )



#
# Drop a table.
#
# @param ret
#   Array to which query results will be added.
# @param table
#   The table to be dropped.
#
def db_drop_table(ret, table):
  DrupyHelper.Reference.check(ref)
  ret.val = update_sql('DROP TABLE {' +  table  + '}')




#
# Add a new field to a table.
#
# @param ret
#   Array to which query results will be added.
# @param table
#   Name of the table to be altered.
# @param field
#   Name of the field to be added.
# @param spec
#   The field specification array, as taken from a schema definition.
#   The specification may also contain the key 'initial', the newly
#   created field will be set to the value of the key in all rows.
#   This is most useful for creating NOT None columns with no default
#   value in existing tables.
# @param keys_new
#   Optional keys and indexes specification to be created on the
#   table along with adding the field. The format is the same as a
#   table specification but without the 'fields' element.  If you are
#   adding a type 'serial' field, you MUST specify at least one key
#   or index including it in this array. @see db_change_field for more
#   explanation why.
#
def db_add_field(ret, table, field, spec, keys_new = []):
  DrupyHelper.Reference.check(ret)
  fixNone = False
  if (not empty(spec['not None']) and not isset(spec, 'default')):
    fixNone = True
    spec['not None'] = False
  query = 'ALTER TABLE {' +  table  + '} ADD '
  query += _db_create_field_sql(field, _db_process_field(spec))
  if (count(keys_new)):
    query += ', ADD ' +  implode(', ADD ', _db_create_keys_sql(keys_new))
  ret.val.append( update_sql(query) )
  if (isset(spec, 'initial')):
    # All this because update_sql does not support %-placeholders.
    sql = 'UPDATE {' +  table  + '} SET ' + field + ' = ' + db_type_placeholder(spec['type'])
    result = db_query(sql, spec['initial'])
    ret.val.append( {'success' : result != False, 'query' : check_plain(sql +  ' ('  + spec['initial'] + ')')})
  if (fixNone):
    spec['not None'] = True
    db_change_field(ret.val, table, field, field, spec)




#
# Drop a field.
#
# @param ret
#   Array to which query results will be added.
# @param table
#   The table to be altered.
# @param field
#   The field to be dropped.
#
def db_drop_field(ret, table, field):
  DrupyHelper.Reference.check(ret)
  ret.val.append( update_sql('ALTER TABLE {' +  table  + '} DROP ' + field) )



#
# Set the default value for a field.
#
# @param ret
#   Array to which query results will be added.
# @param table
#   The table to be altered.
# @param field
#   The field to be altered.
# @param default
#   Default value to be set. None for 'default None'.
#
def db_field_set_default(ret, table, field, default):
  DrupyHelper.Reference.check(ret)
  if (default == None):
    default = 'None'
  else:
    default = ("'default'" if is_string(default) else default)
  ret.append( update_sql('ALTER TABLE {' +  table  + '} ALTER COLUMN ' + field + ' SET DEFAULT ' + default) )



#
# Set a field to have no default value.
#
# @param ret
#   Array to which query results will be added.
# @param table
#   The table to be altered.
# @param field
#   The field to be altered.
#
def db_field_set_no_default(ret, table, field):
  DrupyHelper.Reference.check(ret)
  ret.val.append( update_sql('ALTER TABLE {' +  table  + '} ALTER COLUMN ' + field + ' DROP DEFAULT') )






#
# Add a primary key.
#
# @param ret
#   Array to which query results will be added.
# @param table
#   The table to be altered.
# @param fields
#   Fields for the primary key.
#
def db_add_primary_key(ret, table, fields):
  DrupyHelper.Reference.check(ret)
  ret.val.append( update_sql('ALTER TABLE {' +  table  + '} ADD PRIMARY KEY (' + _db_create_key_sql(fields) +  ')') )



#
# Drop the primary key.
#
# @param ret
#   Array to which query results will be added.
# @param table
#   The table to be altered.
#
def db_drop_primary_key(ret, table):
  DrupyHelper.Reference.check(ret)
  ret.val.append( update_sql('ALTER TABLE {' +  table  + '} DROP PRIMARY KEY') )



#
# Add a unique key.
#
# @param ret
#   Array to which query results will be added.
# @param table
#   The table to be altered.
# @param name
#   The name of the key.
# @param fields
#   An array of field names.
#
def db_add_unique_key(ret, table, name, fields):
  DrupyHelper.Reference.check(ret)
  ret.val.append( update_sql('ALTER TABLE {' +  table  + '} ADD UNIQUE KEY ' + name +  ' ('  + _db_create_key_sql(fields) + ')') )



#
# Drop a unique key.
#
# @param ret
#   Array to which query results will be added.
# @param table
#   The table to be altered.
# @param name
#   The name of the key.
#
def db_drop_unique_key(ret, table, name):
  DrupyHelper.Reference.check(ret)
  ret.val.append( update_sql('ALTER TABLE {' +  table  + '} DROP KEY ' + name) )



#
# Add an index.
#
# @param ret
#   Array to which query results will be added.
# @param table
#   The table to be altered.
# @param name
#   The name of the index.
# @param fields
#   An array of field names.
#
def db_add_index(ret, table, name, fields):
  DrupyHelper.Reference.check(ret)
  query = 'ALTER TABLE {' +  table  + '} ADD INDEX ' + name + ' (' + _db_create_key_sql(fields) + ')'
  ret.val.append( update_sql(query) )



#
# Drop an index.
#
# @param ret
#   Array to which query results will be added.
# @param table
#   The table to be altered.
# @param name
#   The name of the index.
#
def db_drop_index(ret, table, name):
  DrupyHelper.Reference.check(ret)
  ret.val.append( update_sql('ALTER TABLE {' +  table  + '} DROP INDEX ' + name) )




#
# Change a field definition.
#
# IMPORTANT NOTE: To maintain database portability, you have to explicitly
# recreate all indices and primary keys that are using the changed field.
#
# That means that you have to drop all affected keys and indexes with
# db_drop_{primary_key,unique_key,index}() before calling db_change_field().
# To recreate the keys and indices, pass the key definitions as the
# optional keys_new argument directly to db_change_field().
#
# For example, suppose you have:
# @code
# schema['foo'] = array(
#   'fields' : array(
#     'bar' : array('type' : 'int', 'not None' : True)
#   ),
#   'primary key' : array('bar')
# )
# @endcode
# and you want to change foo.bar to be type serial, leaving it as the
# primary key.  The correct sequence is:
# @code
# db_drop_primary_key(ret, 'foo')
# db_change_field(ret, 'foo', 'bar', 'bar',
#   array('type' : 'serial', 'not None' : True),
#   array('primary key' : array('bar')))
# @endcode
#
# The reasons for this are due to the different database engines:
#
# On PostgreSQL, changing a field definition involves adding a new field
# and dropping an old one which* causes any indices, primary keys and
# sequences (from serial-type fields) that use the changed field to be dropped.
#
# On MySQL, all type 'serial' fields must be part of at least one key
# or index as soon as they are created.  You cannot use
# db_add_{primary_key,unique_key,index}() for this purpose because
# the ALTER TABLE command will fail to add the column without a key
# or index specification.  The solution is to use the optional
# keys_new argument to create the key or index at the same time as
# field.
#
# You could use db_add_{primary_key,unique_key,index}() in all cases
# unless you are converting a field to be type serial. You can use
# the keys_new argument in all cases.
#
# @param ret
#   Array to which query results will be added.
# @param table
#   Name of the table.
# @param field
#   Name of the field to change.
# @param field_new
#   New name for the field (set to the same as field if you don't want to change the name).
# @param spec
#   The field specification for the new field.
# @param keys_new
#   Optional keys and indexes specification to be created on the
#   table along with changing the field. The format is the same as a
#   table specification but without the 'fields' element.
#

def db_change_field(ret, table, field, field_new, spec, keys_new = []):
  DrupyHelper.Reference.check(ret)
  sql = 'ALTER TABLE {' +  table  + '} CHANGE ' + field + ' ' + \
    _db_create_field_sql(field_new, _db_process_field(spec))
  if (count(keys_new) > 0):
    sql += ', ADD ' +  implode(', ADD ', _db_create_keys_sql(keys_new))
  ret.val.append( update_sql(sql) )



#
# Returns the last insert id.
#
# @param table
#   The name of the table you inserted into.
# @param field
#   The name of the autoincrement field.
#
def db_last_insert_id(table, field):
  return db_result(db_query('SELECT LAST_INSERT_ID()'))




