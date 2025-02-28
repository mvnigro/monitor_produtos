import pyodbc
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('db_connection.log')
    ]
)
logger = logging.getLogger('db_connection')

class DatabaseConnection:
    """Class to handle database connections and query execution"""
    
    def __init__(self, server, database, username, password, port=1433, timeout=30, retries=3, retry_delay=5):
        """Initialize database connection parameters"""
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self.connection = None
        
        logger.info(f"DatabaseConnection initialized for server: {server}, database: {database}")
    
    def get_connection_string(self):
        """Generate the connection string for SQL Server"""
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server},{self.port};DATABASE={self.database};UID={self.username};PWD={self.password};Connection Timeout={self.timeout}"
    
    def connect(self):
        """Establish a connection to the database with retry logic"""
        attempts = 0
        last_error = None
        
        while attempts < self.retries:
            try:
                logger.info(f"Connecting to database (attempt {attempts + 1}/{self.retries})")
                connection_string = self.get_connection_string()
                self.connection = pyodbc.connect(connection_string)
                logger.info("Database connection established successfully")
                return True, None
            except Exception as e:
                last_error = str(e)
                logger.error(f"Connection attempt {attempts + 1} failed: {last_error}")
                attempts += 1
                if attempts < self.retries:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
        
        logger.error(f"Failed to connect after {self.retries} attempts. Last error: {last_error}")
        return False, last_error
    
    def disconnect(self):
        """Close the database connection"""
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                logger.info("Database connection closed")
                return True, None
            except Exception as e:
                error_msg = f"Error closing database connection: {str(e)}"
                logger.error(error_msg)
                return False, error_msg
        return True, None  # Already disconnected
    
    def execute_query(self, query, params=None):
        """Execute a query and return the results"""
        try:
            # Connect if not already connected
            if not self.connection:
                success, error = self.connect()
                if not success:
                    return None, error
            
            cursor = self.connection.cursor()
            
            # Execute the query
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Get column names
            columns = [column[0] for column in cursor.description] if cursor.description else []
            
            # Fetch results as dictionaries
            results = []
            for row in cursor.fetchall():
                results.append({columns[i]: row[i] for i in range(len(columns))})
            
            cursor.close()
            logger.info(f"Query executed successfully, returned {len(results)} rows")
            return results, None
            
        except Exception as e:
            error_msg = f"Error executing query: {str(e)}"
            logger.error(error_msg)
            
            # Try to reconnect and retry once
            try:
                logger.info("Attempting to reconnect and retry query")
                self.disconnect()
                success, connect_error = self.connect()
                if not success:
                    return None, f"Failed to reconnect: {connect_error}"
                
                cursor = self.connection.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                columns = [column[0] for column in cursor.description] if cursor.description else []
                results = []
                for row in cursor.fetchall():
                    results.append({columns[i]: row[i] for i in range(len(columns))})
                
                cursor.close()
                logger.info(f"Query retry successful, returned {len(results)} rows")
                return results, None
                
            except Exception as retry_error:
                error_msg = f"Error on query retry: {str(retry_error)}"
                logger.error(error_msg)
                return None, error_msg
    
    def execute_non_query(self, query, params=None):
        """Execute a non-query statement (INSERT, UPDATE, DELETE)"""
        try:
            # Connect if not already connected
            if not self.connection:
                success, error = self.connect()
                if not success:
                    return False, error
            
            cursor = self.connection.cursor()
            
            # Execute the query
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Commit the transaction
            self.connection.commit()
            
            affected_rows = cursor.rowcount
            cursor.close()
            
            logger.info(f"Non-query executed successfully, affected {affected_rows} rows")
            return True, None
            
        except Exception as e:
            error_msg = f"Error executing non-query: {str(e)}"
            logger.error(error_msg)
            
            # Try to reconnect and retry once
            try:
                logger.info("Attempting to reconnect and retry non-query")
                self.disconnect()
                success, connect_error = self.connect()
                if not success:
                    return False, f"Failed to reconnect: {connect_error}"
                
                cursor = self.connection.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                self.connection.commit()
                affected_rows = cursor.rowcount
                cursor.close()
                
                logger.info(f"Non-query retry successful, affected {affected_rows} rows")
                return True, None
                
            except Exception as retry_error:
                error_msg = f"Error on non-query retry: {str(retry_error)}"
                logger.error(error_msg)
                return False, error_msg
    
    def test_connection(self):
        """Test the database connection and return diagnostics"""
        diagnostics = {
            "server": self.server,
            "database": self.database,
            "port": self.port,
            "username": self.username,
            "password": "*****",  # Masked for security
            "timeout": self.timeout,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "driver_info": None,
            "server_info": None
        }
        
        try:
            # Try to connect
            connection_string = self.get_connection_string()
            conn = pyodbc.connect(connection_string)
            
            # Get driver and server info
            cursor = conn.cursor()
            diagnostics["driver_info"] = conn.getinfo(pyodbc.SQL_DRIVER_NAME)
            
            # Get SQL Server version
            cursor.execute("SELECT @@VERSION AS Version")
            row = cursor.fetchone()
            if row:
                diagnostics["server_info"] = row.Version
            
            # Test a simple query
            cursor.execute("SELECT 1 AS TestResult")
            row = cursor.fetchone()
            test_result = row.TestResult if row else None
            
            cursor.close()
            conn.close()
            
            logger.info("Connection test successful")
            return True, "Connection successful", diagnostics
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Connection test failed: {error_msg}")
            diagnostics["error"] = error_msg
            
            # Try to determine if it's a driver issue
            try:
                drivers = pyodbc.drivers()
                diagnostics["available_drivers"] = drivers
                if not any("SQL Server" in driver for driver in drivers):
                    diagnostics["possible_cause"] = "No SQL Server drivers found"
            except:
                pass
                
            return False, f"Connection failed: {error_msg}", diagnostics