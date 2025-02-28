import logging

logger = logging.getLogger('db_explorer')

class DatabaseExplorer:
    """Class to explore database schema and tables"""
    
    def __init__(self, db_connection):
        """Initialize with a database connection"""
        self.db = db_connection
        logger.info("DatabaseExplorer initialized")
    
    def list_tables(self, schema=None):
        """List all tables in the database or in a specific schema"""
        try:
            query = """
                SELECT 
                    t.TABLE_SCHEMA as schema_name,
                    t.TABLE_NAME as table_name,
                    t.TABLE_TYPE as table_type
                FROM 
                    INFORMATION_SCHEMA.TABLES t
            """
            
            if schema:
                query += " WHERE t.TABLE_SCHEMA = ?"
                tables, error = self.db.execute_query(query, [schema])
            else:
                query += " ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME"
                tables, error = self.db.execute_query(query)
            
            if error:
                logger.error(f"Error listing tables: {error}")
                return [], error
            
            return tables, None
        except Exception as e:
            error_msg = f"Error listing tables: {str(e)}"
            logger.exception(error_msg)
            return [], error_msg
    
    def list_schemas(self):
        """List all schemas in the database"""
        try:
            query = """
                SELECT 
                    SCHEMA_NAME as schema_name,
                    SCHEMA_OWNER as schema_owner
                FROM 
                    INFORMATION_SCHEMA.SCHEMATA
                ORDER BY 
                    SCHEMA_NAME
            """
            
            schemas, error = self.db.execute_query(query)
            
            if error:
                logger.error(f"Error listing schemas: {error}")
                return [], error
            
            return schemas, None
        except Exception as e:
            error_msg = f"Error listing schemas: {str(e)}"
            logger.exception(error_msg)
            return [], error_msg
    
    def list_columns(self, table_name, schema_name=None):
        """List all columns in a table"""
        try:
            query = """
                SELECT 
                    c.COLUMN_NAME as column_name,
                    c.DATA_TYPE as data_type,
                    c.CHARACTER_MAXIMUM_LENGTH as max_length,
                    c.IS_NULLABLE as is_nullable,
                    COLUMNPROPERTY(OBJECT_ID(c.TABLE_SCHEMA + '.' + c.TABLE_NAME), c.COLUMN_NAME, 'IsIdentity') as is_identity
                FROM 
                    INFORMATION_SCHEMA.COLUMNS c
                WHERE 
                    c.TABLE_NAME = ?
            """
            
            params = [table_name]
            
            if schema_name:
                query += " AND c.TABLE_SCHEMA = ?"
                params.append(schema_name)
            
            query += " ORDER BY c.ORDINAL_POSITION"
            
            columns, error = self.db.execute_query(query, params)
            
            if error:
                logger.error(f"Error listing columns for table {table_name}: {error}")
                return [], error
            
            return columns, None
        except Exception as e:
            error_msg = f"Error listing columns for table {table_name}: {str(e)}"
            logger.exception(error_msg)
            return [], error_msg
    
    def table_exists(self, table_name, schema_name=None):
        """Check if a table exists in the database"""
        try:
            query = """
                SELECT 
                    1
                FROM 
                    INFORMATION_SCHEMA.TABLES t
                WHERE 
                    t.TABLE_NAME = ?
            """
            
            params = [table_name]
            
            if schema_name:
                query += " AND t.TABLE_SCHEMA = ?"
                params.append(schema_name)
            
            result, error = self.db.execute_query(query, params)
            
            if error:
                logger.error(f"Error checking if table {table_name} exists: {error}")
                return False, error
            
            return len(result) > 0, None
        except Exception as e:
            error_msg = f"Error checking if table {table_name} exists: {str(e)}"
            logger.exception(error_msg)
            return False, error_msg
    
    def search_similar_tables(self, search_term):
        """Search for tables with names similar to the search term"""
        try:
            # Use LIKE operator for pattern matching
            query = """
                SELECT 
                    t.TABLE_SCHEMA as schema_name,
                    t.TABLE_NAME as table_name,
                    t.TABLE_TYPE as table_type
                FROM 
                    INFORMATION_SCHEMA.TABLES t
                WHERE 
                    t.TABLE_NAME LIKE ?
                ORDER BY 
                    t.TABLE_SCHEMA, t.TABLE_NAME
            """
            
            # Add wildcards to search term
            search_pattern = f"%{search_term}%"
            
            tables, error = self.db.execute_query(query, [search_pattern])
            
            if error:
                logger.error(f"Error searching for similar tables: {error}")
                return [], error
            
            return tables, None
        except Exception as e:
            error_msg = f"Error searching for similar tables: {str(e)}"
            logger.exception(error_msg)
            return [], error_msg
    
    def get_table_row_count(self, table_name, schema_name=None):
        """Get the number of rows in a table"""
        try:
            # Build the fully qualified table name
            full_table_name = f"{schema_name}.{table_name}" if schema_name else table_name
            
            query = f"SELECT COUNT(*) as row_count FROM {full_table_name}"
            
            result, error = self.db.execute_query(query)
            
            if error:
                logger.error(f"Error getting row count for table {full_table_name}: {error}")
                return 0, error
            
            if result and len(result) > 0:
                return result[0]['row_count'], None
            else:
                return 0, None
        except Exception as e:
            error_msg = f"Error getting row count for table {table_name}: {str(e)}"
            logger.exception(error_msg)
            return 0, error_msg