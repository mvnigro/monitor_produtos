from flask import Flask, render_template, jsonify, request, redirect, url_for
import os
import json
import random
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from flask_apscheduler import APScheduler
import logging
import socket
from utils.db_connection import DatabaseConnection
from utils.db_explorer import DatabaseExplorer
from utils.mock_data import get_mock_orders, get_mock_stats, mark_mock_order_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger('app')

# Load environment variables
load_dotenv()

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
scheduler = APScheduler()

# Database connection parameters
DB_SERVER = os.getenv('DB_SERVER')
DB_DATABASE = os.getenv('DB_DATABASE')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_PORT = int(os.getenv('DB_PORT', '1433'))  # Default SQL Server port
DB_TIMEOUT = int(os.getenv('DB_TIMEOUT', '30'))  # Default 30 seconds
DB_RETRIES = int(os.getenv('DB_RETRIES', '3'))   # Default 3 retries
DB_RETRY_DELAY = int(os.getenv('DB_RETRY_DELAY', '5'))  # Default 5 seconds delay
DB_SCHEMA = os.getenv('DB_SCHEMA', 'dbo')  # Default schema name
OFFLINE_MODE = os.getenv('OFFLINE_MODE', 'false').lower() == 'true'

# Path for completed orders JSON file
COMPLETED_ORDERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(COMPLETED_ORDERS_DIR, exist_ok=True)

# Add a new constant for tracking completed orders
COMPLETION_TRACKING_TIME = int(os.getenv('COMPLETION_TRACKING_TIME', '48'))  # Hours to track completions

# Add more robust tracking for completed orders
COMPLETION_TRACKING = {
    'client_products': set(),  # Set of "client_name:product_code" strings
    'last_cleanup': datetime.now(),
    'persisted_to_disk': False,
    'loaded_from_disk': False
}

# Path for tracking completed orders persistence
COMPLETION_TRACKING_FILE = os.path.join(COMPLETED_ORDERS_DIR, 'completion_tracking.json')

# Cache for data
data_cache = {
    'pending_orders': [],
    'last_update': None,
    'stats': {
        'product_labels': [],   # Changed from separator_labels
        'product_counts': []    # Changed from separator_counts
    },
    'is_cache': False,  # Flag to indicate if data is from cache
    'connection_status': {
        'last_check': None,
        'status': 'unknown',  # 'connected', 'disconnected', 'unknown'
        'diagnostics': {},
        'error_message': None
    }
}

# Create database connection helper
db = DatabaseConnection(
    server=DB_SERVER,
    database=DB_DATABASE,
    username=DB_USERNAME,
    password=DB_PASSWORD,
    port=DB_PORT,
    timeout=DB_TIMEOUT,
    retries=DB_RETRIES,
    retry_delay=DB_RETRY_DELAY
)

# Create database explorer helper
db_explorer = DatabaseExplorer(db)

@app.template_filter('format_datetime')
def format_datetime(value, format='%H:%M:%S'):
    """Format a datetime string"""
    if not value:
        return ''
    try:
        if 'T' in value:
            # ISO format
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.strftime(format)
        else:
            # Other format
            return value
    except Exception:
        return value

def get_completion_key(client_name, product_code):
    """Generate a unique key for tracking completed orders - more robust implementation with type checking"""
    if not client_name or product_code is None:  # Changed condition to handle 0 as valid product_code
        logger.warning(f"Invalid completion key generation attempt: client='{client_name}', product='{product_code}'")
        return None
        
    # Ensure product_code is a string
    if not isinstance(product_code, str):
        try:
            product_code = str(product_code)
            logger.debug(f"Converted product_code from {type(product_code)} to string: '{product_code}'")
        except Exception as e:
            logger.error(f"Failed to convert product_code to string: {e}")
            return None
    
    # Ensure client_name is a string
    if not isinstance(client_name, str):
        try:
            client_name = str(client_name)
            logger.debug(f"Converted client_name from {type(client_name)} to string: '{client_name}'")
        except Exception as e:
            logger.error(f"Failed to convert client_name to string: {e}")
            return None
        
    # Create a normalized version of the client name (lowercase, no spaces, alphanumeric only)
    normalized_client = ''.join(c.lower() for c in client_name if c.isalnum())
    # Create a normalized version of the product code (lowercase, no spaces)
    normalized_product = ''.join(c.lower() for c in product_code if c not in ' -_')
    
    key = f"{normalized_client}:{normalized_product}"
    logger.debug(f"Generated completion key: {key} from client='{client_name}', product='{product_code}'")
    return key

def was_order_completed(client_name, product_code):
    """Check if an order was already completed - with better logging"""
    key = get_completion_key(client_name, product_code)
    if not key:
        return False
        
    is_completed = key in COMPLETION_TRACKING['client_products']
    if is_completed:
        logger.debug(f"Order found in completion tracking: {client_name} - {product_code}")
    return is_completed

def mark_order_completed(client_name, product_code):
    """Mark an order as completed in the tracking system with immediate persistence"""
    key = get_completion_key(client_name, product_code)
    if not key:
        logger.error(f"Failed to mark order as completed: Invalid key for {client_name} - {product_code}")
        return False
        
    COMPLETION_TRACKING['client_products'].add(key)
    logger.info(f"Marked order as completed: {client_name} - {product_code}")
    
    # Save tracking to disk immediately for persistence
    save_completion_tracking()
    
    # Perform cleanup of old completions if needed
    current_time = datetime.now()
    hours_since_cleanup = (current_time - COMPLETION_TRACKING['last_cleanup']).total_seconds() / 3600
    
    # Only clean up once every 6 hours
    if hours_since_cleanup >= 6:
        cleanup_old_completions()
        COMPLETION_TRACKING['last_cleanup'] = current_time
    
    return True

def save_completion_tracking():
    """Save current completion tracking to disk for persistence"""
    try:
        tracking_data = {
            'client_products': list(COMPLETION_TRACKING['client_products']),
            'last_cleanup': COMPLETION_TRACKING['last_cleanup'].isoformat(),
            'last_updated': datetime.now().isoformat()
        }
        
        with open(COMPLETION_TRACKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(tracking_data, f, ensure_ascii=False, indent=2)
            
        COMPLETION_TRACKING['persisted_to_disk'] = True
        logger.info(f"Saved {len(COMPLETION_TRACKING['client_products'])} completion tracking entries to disk")
        return True
    except Exception as e:
        logger.exception(f"Error saving completion tracking to disk: {e}")
        return False

def load_completion_tracking():
    """Load completed orders tracking from disk and rebuild from report files if needed"""
    global COMPLETION_TRACKING
    
    # First try to load from tracking file for performance
    if os.path.exists(COMPLETION_TRACKING_FILE):
        try:
            with open(COMPLETION_TRACKING_FILE, 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)
                
            # Ensure client_products is always converted to a set, even if it's stored as a list in the JSON
            COMPLETION_TRACKING['client_products'] = set(tracking_data.get('client_products', []))
            COMPLETION_TRACKING['last_cleanup'] = datetime.fromisoformat(tracking_data.get('last_cleanup'))
            COMPLETION_TRACKING['loaded_from_disk'] = True
            
            logger.info(f"Loaded {len(COMPLETION_TRACKING['client_products'])} completion entries from tracking file")
            
            # Still rebuild from reports for safety, but only from today and yesterday
            rebuild_tracking_from_recent_reports()
            
            return True
        except Exception as e:
            logger.error(f"Error loading completion tracking from file: {e}")
            # Continue to rebuild from reports
    
    # Rebuild tracking from the saved JSON files if tracking file failed or doesn't exist
    rebuild_tracking_from_all_reports()
    return True

def rebuild_tracking_from_all_reports():
    """Rebuild the entire completion tracking from all report files"""
    # Recalculate tracking from the saved JSON files
    COMPLETION_TRACKING['client_products'] = set()
    
    # Define the date range to track
    end_date = date.today()
    start_date = end_date - timedelta(days=30)  # Track up to 30 days back
    
    # Iterate through days in the range
    current_date = start_date
    while current_date <= end_date:
        # Load completions for this day
        load_day_completions_into_tracking(current_date)
        
        # Move to next day
        current_date += timedelta(days=1)
    
    # Update last cleanup timestamp
    COMPLETION_TRACKING['last_cleanup'] = datetime.now()
    
    logger.info(f"Rebuilt tracking with {len(COMPLETION_TRACKING['client_products'])} completed orders")
    
    # Save the rebuilt tracking for future use
    save_completion_tracking()

def rebuild_tracking_from_recent_reports():
    """Rebuild tracking only from today and yesterday's reports for performance"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # Load completions for yesterday and today to catch any recent missing ones
    load_day_completions_into_tracking(yesterday)
    load_day_completions_into_tracking(today)
    
    # Save any new entries found
    save_completion_tracking()

def load_day_completions_into_tracking(report_date):
    """Load completions for a specific day into tracking"""
    orders = load_completed_orders(report_date)
    
    # Add each completion to tracking
    added_count = 0
    for order in orders:
        client_name = order.get('client_name')
        product_code = order.get('product_code')
        if client_name and product_code:
            key = get_completion_key(client_name, product_code)
            if key and key not in COMPLETION_TRACKING['client_products']:
                COMPLETION_TRACKING['client_products'].add(key)
                added_count += 1
    
    if added_count > 0:
        logger.debug(f"Added {added_count} completions from {report_date} to tracking")

def generate_order_id(order_data):
    """Generate a unique ID for a completed order"""
    # Create a composite identifier
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    client_code = ''.join(e for e in order_data.get('client_name', '')[:5] if e.isalnum())
    product_code = order_data.get('product_code', '')[:5]
    random_suffix = ''.join(random.choices('0123456789', k=3))
    
    return f"{timestamp}-{client_code}-{product_code}-{random_suffix}"

def get_completion_file_path(report_date=None):
    """Get the path for the completion file for a specific date"""
    if report_date is None:
        report_date = date.today()
    
    if isinstance(report_date, str):
        try:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        except ValueError:
            report_date = date.today()
    
    date_str = report_date.strftime('%Y-%m-%d')
    file_path = os.path.join(COMPLETED_ORDERS_DIR, f'completed_{date_str}.json')
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    return file_path

def load_completed_orders(report_date=None):
    """Load completed orders for a specific date"""
    file_path = get_completion_file_path(report_date)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:  # Check if file is not empty
                    return json.loads(content)
                return []  # Return empty list if file is empty
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error when loading completed orders: {e}")
        except Exception as e:
            logger.error(f"Error loading completed orders: {e}")
    return []

def save_completed_order(order_data):
    """Save a completed order to the JSON file with improved type checking and error handling"""
    file_path = get_completion_file_path()
    
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Load existing data
        completed_orders = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # Check if file is not empty
                        completed_orders = json.loads(content)
                    # If file is empty, use an empty list (already initialized)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error when reading completion file: {e}")
                # Use an empty list if the file is corrupted
                completed_orders = []
            except Exception as e:
                logger.exception(f"Error reading completion file: {e}")
                completed_orders = []
        
        # Sanitize order data to ensure all values are JSON serializable
        sanitized_data = {}
        for key, value in order_data.items():
            if value is None:
                sanitized_data[key] = 'N/A'
            elif isinstance(value, (str, int, float, bool)):
                sanitized_data[key] = value
            else:
                try:
                    sanitized_data[key] = str(value)
                except Exception as e:
                    logger.error(f"Error converting {key}={value} to string: {e}")
                    sanitized_data[key] = 'N/A'
        
        # Add timestamp and processing metadata
        sanitized_data['timestamp'] = datetime.now().isoformat()
        sanitized_data['processing_date'] = date.today().isoformat()
        sanitized_data['id'] = generate_order_id(sanitized_data)
        
        # Ensure all critical fields are strings
        for field in ['product_code', 'product_name', 'client_name', 'completed_by', 'separador']:
            if field in sanitized_data:
                if sanitized_data[field] is None:
                    sanitized_data[field] = 'N/A'  # Replace None with N/A
                elif not isinstance(sanitized_data[field], str):
                    sanitized_data[field] = str(sanitized_data[field])  # Convert to string
        
        # Add to the list
        completed_orders.append(sanitized_data)
        
        # Write to file with explicit error handling
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(completed_orders, f, ensure_ascii=False, indent=2, default=str)
        except Exception as write_error:
            logger.exception(f"Error writing to completion file: {write_error}")
            return False, f"Error writing to file: {str(write_error)}"
            
        # Mark as completed in tracking
        client_name = sanitized_data.get('client_name')
        product_code = sanitized_data.get('product_code')
        
        # Extra safety checks
        if product_code is None:
            logger.warning("product_code is None in completed order data")
            product_code = "unknown"
        
        if client_name is None:
            logger.warning("client_name is None in completed order data")
            client_name = "unknown"
        
        if client_name and product_code:
            try:
                mark_order_completed(client_name, product_code)
            except Exception as tracking_error:
                logger.exception(f"Error marking order as completed in tracking: {tracking_error}")
                # Continue anyway, this is not critical
                
        logger.info(f"Order completed successfully: {client_name} - {product_code}")
        return True, None
    except Exception as e:
        logger.exception(f"Error saving completed order: {e}")
        return False, str(e)

def get_pending_orders():
    """Fetch pending orders from the database with improved completion filtering."""
    global OFFLINE_MODE
    
    # If offline mode is enabled, return mock data
    if OFFLINE_MODE:
        logger.info("Using mock data (offline mode enabled)")
        mock_orders = get_mock_orders()
        data_cache['pending_orders'] = mock_orders
        data_cache['last_update'] = datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
        data_cache['stats'] = get_mock_stats()
        data_cache['is_cache'] = False
        data_cache['connection_status']['status'] = 'offline'
        data_cache['connection_status']['last_check'] = datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
        return mock_orders
    
    try:
        # Use schema prefix for table names
        schema_prefix = f"{DB_SCHEMA}." if DB_SCHEMA else ""
        
        # Updated query to correctly filter out records with "SACO" or "CAIXA" in Ocorrencia_Texto and Prod_Desc
        query = f"""
            SELECT 
                FORMAT(Ocorrencia_Data, 'dd/MM/yyyy, HH:mm:ss') as Data_Ocorrencia,
                Separador,
                Cli_Nome as Cliente,
                Prod_Desc as Produto,
                Pedido_Status,
                Ocorrencia_Tipo,
                Ocorrencia_Texto,
                Produto_Codigo
            FROM 
                {schema_prefix}VIEW_PB_NF_Cancelada
            WHERE 
                Pedido_Status = 'Conferido'
                AND Ocorrencia_Tipo = 'Espera por Produto'
              
            ORDER BY 
                Ocorrencia_Data DESC
        """
        
        results, error = db.execute_query(query)
        
        # Update connection status
        data_cache['connection_status']['last_check'] = datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
        
        if (error):
            logger.error(f"Error executing query: {error}")
            data_cache['connection_status']['status'] = 'disconnected'
            data_cache['connection_status']['error_message'] = str(error)
            
            # Check for specific table not found error
            if "Invalid object name" in str(error):
                # Try to find similar tables to help debugging
                table_name = str(error).split("'")[1] if "'" in str(error) else "Ocorrencias"
                table_name = table_name.replace(f"{schema_prefix}", "")  # Remove schema prefix if present
                similar_tables, _ = db_explorer.search_similar_tables(table_name.split(".")[0])
                
                if (similar_tables):
                    logger.info(f"Found {len(similar_tables)} similar tables: {', '.join([t['table_name'] for t in similar_tables])}")
                    data_cache['connection_status']['similar_tables'] = similar_tables
            
            # Return cached data if available
            if data_cache['pending_orders']:
                logger.info("Using cached data due to database error")
                data_cache['is_cache'] = True
                return data_cache['pending_orders']
                
            # If no cached data, try mock data
            logger.info("No cached data available, using mock data")
            mock_orders = get_mock_orders()
            data_cache['pending_orders'] = mock_orders
            data_cache['stats'] = get_mock_stats()
            data_cache['is_cache'] = True
            return mock_orders
        
        # Process the results
        processed_results = []
        product_groups = {}  # Dictionary to group by products
        
        # Reset stats
        stats = {
            'product_labels': [],
            'product_counts': []
        }
        
        # First pass: group by product and collect clients with individual details
        for row in results:
            # Format product name for display and stats
            product_name = f"{row['Produto']} ({row['Produto_Codigo']})"
            client_name = row['Cliente']
            product_code = row['Produto_Codigo']
            
            # Type validation to prevent errors
            if not isinstance(product_code, str):
                try:
                    product_code = str(product_code)
                    logger.debug(f"Converted product_code from {type(product_code)} to string: '{product_code}'")
                except Exception as e:
                    logger.error(f"Failed to convert product_code to string: {e}")
                    continue  # Skip this row on conversion error
            
            if not isinstance(client_name, str):
                try:
                    client_name = str(client_name)
                    logger.debug(f"Converted client_name from {type(client_name)} to string: '{client_name}'")
                except Exception as e:
                    logger.error(f"Failed to convert client_name to string: {e}")
                    continue  # Skip this row on conversion error
            
            # Skip this client-product combination if it was already completed - now with more robust type checking
            try:
                completion_key = get_completion_key(client_name, product_code)
                if completion_key in COMPLETION_TRACKING['client_products']:
                    logger.debug(f"Filtering out completed order: {client_name} - {product_code}")
                    continue
            except Exception as e:
                logger.error(f"Error checking completion status: {e}")
                # Continue processing this row even if the completion check fails
            
            # Store client info with individual details
            client_info = {
                'nome': client_name,
                'data_ocorrencia': row['Data_Ocorrencia'],
                'separador': row['Separador'],
                'texto_ocorrencia': row['Ocorrencia_Texto']
            }
            
            # Add to product groups
            if (product_name not in product_groups):
                product_groups[product_name] = {
                    'produto': product_name,
                    'codigo': row['Produto_Codigo'],
                    'clientes_detalhes': [client_info],  # List of client detail objects
                    'clientes': [client_name],  # Keep simple client name list for backwards compatibility
                    'tipo_ocorrencia': row['Ocorrencia_Tipo'],
                    'status': row['Pedido_Status'],
                    # Use the most recent date for the main product record
                    'data_ocorrencia': row['Data_Ocorrencia']
                }
            else:
                # Add client if not already in the list
                if client_name not in product_groups[product_name]['clientes']:
                    product_groups[product_name]['clientes'].append(client_name)
                    product_groups[product_name]['clientes_detalhes'].append(client_info)
                    
                    # Update the product date if this occurrence is more recent
                    current_date_str = product_groups[product_name]['data_ocorrencia']
                    if row['Data_Ocorrencia'] > current_date_str:
                        product_groups[product_name]['data_ocorrencia'] = row['Data_Ocorrencia']
        
        # Second pass: create the final processed results
        for product_name, product_data in product_groups.items():
            # Skip products with no clients (all might have been filtered as completed)
            if not product_data['clientes']:
                continue
                
            # Count the number of clients for this product
            client_count = len(product_data['clientes'])
            
            # Format the clients as a string with count
            product_data['cliente'] = f"{client_count} cliente(s): {', '.join(product_data['clientes'])}"
            
            # Add to processed results
            processed_results.append(product_data)
            
            # Update stats
            stats['product_labels'].append(product_name)
            stats['product_counts'].append(client_count)
        
        # Sort results by number of clients (descending)
        processed_results = sorted(processed_results, key=lambda x: len(x['clientes']), reverse=True)
        
        # Update cache
        data_cache['pending_orders'] = processed_results
        data_cache['last_update'] = datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
        data_cache['stats'] = stats
        data_cache['is_cache'] = False
        data_cache['connection_status']['status'] = 'connected'
        data_cache['connection_status']['error_message'] = None
        
        return processed_results
    except Exception as e:
        logger.exception(f"Unexpected error fetching pending orders: {str(e)}")
        data_cache['connection_status']['status'] = 'error'
        data_cache['connection_status']['error_message'] = str(e)
        
        # Return cached data if available
        if data_cache['pending_orders']:
            logger.info("Using cached data due to unexpected error")
            data_cache['is_cache'] = True
            return data_cache['pending_orders']
            
        # If no cached data, use mock data
        mock_orders = get_mock_orders()
        data_cache['pending_orders'] = mock_orders
        data_cache['stats'] = get_mock_stats()
        data_cache['is_cache'] = True
        return mock_orders

def get_available_report_dates():
    """Get a list of all dates for which reports are available"""
    dates = []
    try:
        # Look for all completed_*.json files
        for filename in os.listdir(COMPLETED_ORDERS_DIR):
            if filename.startswith('completed_') and filename.endswith('.json'):
                date_part = filename[len('completed_'):-len('.json')]
                try:
                    # Parse the date and add to list
                    report_date = datetime.strptime(date_part, '%Y-%m-%d').date()
                    dates.append({
                        'date': report_date.isoformat(),
                        'formatted_date': report_date.strftime('%d/%m/%Y'),
                    })
                except ValueError:
                    continue
    except Exception as e:
        logger.error(f"Error listing report dates: {e}")
        
    # Sort dates in reverse order (newest first)
    dates.sort(key=lambda x: x['date'], reverse=True)
    return dates

@app.route('/')
def index():
    """Render the main dashboard page."""
    # Get pending orders (from cache if available)
    pending_orders = get_pending_orders()
    
    return render_template('index.html', 
                          pending_orders=pending_orders, 
                          total_pending=len(pending_orders),
                          last_update=data_cache['last_update'],
                          is_cache=data_cache['is_cache'],
                          connection_status=data_cache['connection_status']['status'],
                          offline_mode=OFFLINE_MODE,
                          now=datetime.now())

@app.route('/api/pending-orders')
def api_pending_orders():
    """API endpoint to get pending orders."""
    orders = get_pending_orders()
    return jsonify({
        'orders': orders, 
        'is_cache': data_cache['is_cache'],
        'last_update': data_cache['last_update'],
        'connection_status': data_cache['connection_status']['status']
    })

@app.route('/api/stats')
def get_stats():
    """API endpoint to get statistics about pending orders."""
    try:
        # Refresh data if needed
        get_pending_orders()
        
        return jsonify({
            'stats': data_cache['stats'],
            'is_cache': data_cache['is_cache'],
            'last_update': data_cache['last_update'],
            'connection_status': data_cache['connection_status']['status']
        })
    except Exception as e:
        logger.exception(f"Error getting stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh', methods=['GET'])
def api_refresh():
    """API endpoint to refresh data."""
    try:
        get_pending_orders()
        return jsonify({
            'success': True,
            'is_cache': data_cache['is_cache'],
            'last_update': data_cache['last_update'],
            'connection_status': data_cache['connection_status']['status'],
            'error_message': data_cache['connection_status'].get('error_message')
        })
    except Exception as e:
        logger.exception(f"Error refreshing data: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/complete-order', methods=['POST'])
def complete_order():
    """API endpoint to mark an order as completed with improved validation and persistence"""
    try:
        data = request.json
        logger.info(f"Received completion request: {data}")
        
        # Enhanced validation with better error messages
        if not data:
            logger.error("Empty request data received")
            return jsonify({
                'success': False,
                'error': 'Dados vazios ou inválidos.'
            }), 400
            
        # Check each field individually for better error messages
        missing_fields = []
        if not data.get('product_code'):
            missing_fields.append('código do produto')
        if not data.get('product_name'):
            missing_fields.append('nome do produto')
        if not data.get('client_name'):
            missing_fields.append('nome do cliente')
        if not data.get('completed_by'):
            missing_fields.append('nome do funcionário')
            
        if missing_fields:
            error_msg = f"Dados incompletos. Os seguintes campos são obrigatórios: {', '.join(missing_fields)}."
            logger.error(f"Validation error: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
            
        # Add some additional metadata
        data['client_ip'] = request.remote_addr
        data['user_agent'] = str(request.user_agent)
        client_name = data.get('client_name')
        product_code = data.get('product_code')
        
        # Enhanced validation for client name and product code
        if not client_name or not product_code:
            return jsonify({
                'success': False,
                'error': 'Cliente e código do produto são obrigatórios e não podem estar vazios.'
            }), 400
            
        # Make sure string fields are strings (important for non-string inputs)
        for field in ['product_code', 'product_name', 'client_name', 'completed_by', 'separador']:
            if field in data:
                if data[field] is None:
                    data[field] = 'N/A'  # Replace None with N/A
                else:
                    try:
                        data[field] = str(data[field])  # Convert to string with explicit error handling
                    except Exception as e:
                        logger.warning(f"Failed to convert {field} to string: {e}, using 'N/A' instead")
                        data[field] = 'N/A'
        
        # Ensure separador is never None or empty
        if not data.get('separador'):
            data['separador'] = 'N/A'
            
        # If in offline/mock mode, handle differently
        if OFFLINE_MODE:
            # Mark as completed in mock data
            mark_mock_order_completed(client_name, product_code)
            # Still save the record for reporting
            success, error = save_completed_order(data)
            
            if not success:
                logger.error(f"Failed to save completed order in offline mode: {error}")
                return jsonify({
                    'success': False,
                    'error': f'Erro ao salvar registro: {error}'
                }), 500
                
            return jsonify({
                'success': True,
                'message': 'Pedido marcado como concluído com sucesso (modo offline).'
            })
        
        # Debug the data before saving to help troubleshoot
        logger.debug(f"Order data before saving: {json.dumps(data, ensure_ascii=False, default=str)}")
        
        # Normal mode - save the completion record with more robust error handling
        try:
            success, error = save_completed_order(data)
        except Exception as specific_error:
            logger.exception(f"Exception during save_completed_order: {specific_error}")
            return jsonify({
                'success': False,
                'error': f'Erro ao salvar registro: {str(specific_error)}'
            }), 500
        
        if success:
            # Mark this client-product combination as completed in our tracking
            try:
                tracking_success = mark_order_completed(client_name, product_code)
                if not tracking_success:
                    logger.warning(f"Failed to mark order as completed in tracking: {client_name} - {product_code}")
                    # Continue anyway, this is not critical
            except Exception as tracking_error:
                logger.exception(f"Error in mark_order_completed: {tracking_error}")
                # Continue anyway, this is not critical
            
            # Force refresh of the data cache
            try:
                refresh_data_cache()
            except Exception as cache_error:
                logger.exception(f"Error refreshing data cache: {cache_error}")
                # Continue anyway, this is not critical
                
            return jsonify({
                'success': True,
                'message': 'Pedido marcado como concluído com sucesso.'
            })
        else:
            logger.error(f"Failed to save completed order: {error}")
            return jsonify({
                'success': False,
                'error': f'Erro ao salvar registro: {error}'
            }), 500
            
    except Exception as e:
        logger.exception(f"Error completing order: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

def refresh_data_cache():
    """Force refresh of the data cache"""
    global data_cache
    data_cache['pending_orders'] = []
    data_cache['is_cache'] = False
    get_pending_orders()

@app.route('/report')
@app.route('/completed')
def completed_orders():
    """Render the completed orders page"""
    # Get date from query param, defaulting to today
    date_str = request.args.get('date')
    if date_str:
        try:
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            report_date = date.today()
    else:
        report_date = date.today()
        
    # Load orders for selected date
    completed_orders = load_completed_orders(report_date)
    
    # Group by employee
    employees = {}
    for order in completed_orders:
        employee = order.get('completed_by', 'Desconhecido')
        if employee not in employees:
            employees[employee] = []
        employees[employee].append(order)
    
    # Get today's date for template comparison
    today_date = date.today()
    
    return render_template('completed.html',
                          completed_orders=completed_orders,
                          employees=employees,
                          report_date=report_date.strftime('%d/%m/%Y'),
                          report_date_iso=report_date.isoformat(),
                          last_update=datetime.now().strftime('%d/%m/%Y, %H:%M:%S'),
                          is_cache=False,
                          connection_status=data_cache['connection_status']['status'],
                          total_count=len(completed_orders))

@app.route('/api/reports/dates')
def get_available_report_dates_api():
    """API endpoint to get all dates for which reports are available"""
    try:
        available_dates = get_available_report_dates()
        return jsonify({
            'success': True,
            'dates': available_dates
        })
    except Exception as e:
        logger.exception(f"Error getting report dates: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/delete-order', methods=['POST'])
def delete_order():
    """API endpoint to delete a completed order"""
    try:
        data = request.json
        logger.info(f"Received delete order request: {data}")
        
        # Validate required fields
        if not data or not data.get('order_id'):
            return jsonify({
                'success': False,
                'error': 'ID do pedido é obrigatório.'
            }), 400
            
        order_id = data.get('order_id')
        report_date = data.get('report_date')
        
        # If no report date is provided, use today's date
        if not report_date:
            report_date = date.today().isoformat()
        
        # Get the file path for the specified date
        file_path = get_completion_file_path(report_date)
        
        # Check if the file exists
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': f'Não foram encontrados registros para a data {report_date}.'
            }), 404
            
        # Load the orders from the file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    completed_orders = json.loads(content)
                else:
                    completed_orders = []
        except Exception as e:
            logger.exception(f"Error reading completion file: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro ao ler arquivo de registros: {str(e)}'
            }), 500
            
        # Find the order to delete
        order_to_delete = None
        for i, order in enumerate(completed_orders):
            if order.get('id') == order_id:
                order_to_delete = order
                del completed_orders[i]
                break
                
        if not order_to_delete:
            return jsonify({
                'success': False,
                'error': 'Pedido não encontrado.'
            }), 404
            
        # Save the updated orders list back to the file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(completed_orders, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.exception(f"Error writing to completion file: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro ao atualizar arquivo de registros: {str(e)}'
            }), 500
            
        # Remove from completion tracking if needed
        client_name = order_to_delete.get('client_name')
        product_code = order_to_delete.get('product_code')
        
        if client_name and product_code:
            try:
                # Only remove from tracking if this is the only record for this client-product combination
                # Check if there are other completed orders for this client-product
                other_completions_exist = False
                for order in completed_orders:
                    if (order.get('client_name') == client_name and 
                        order.get('product_code') == product_code):
                        other_completions_exist = True
                        break
                        
                # If no other completions exist, remove from tracking
                if not other_completions_exist:
                    key = get_completion_key(client_name, product_code)
                    if key and key in COMPLETION_TRACKING['client_products']:
                        COMPLETION_TRACKING['client_products'].remove(key)
                        save_completion_tracking()
                        logger.info(f"Removed from completion tracking: {client_name} - {product_code}")
            except Exception as e:
                logger.exception(f"Error updating completion tracking: {e}")
                # Continue anyway, this is not critical
                
        # Force refresh of the data cache
        try:
            refresh_data_cache()
        except Exception as e:
            logger.exception(f"Error refreshing data cache: {e}")
            # Continue anyway, this is not critical
            
        return jsonify({
            'success': True,
            'message': 'Pedido excluído com sucesso.'
        })
        
    except Exception as e:
        logger.exception(f"Error deleting order: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@app.route('/api/reports/export', methods=['GET'])
def export_report_api():
    """API endpoint to export report data as JSON"""
    try:
        # Get date from query param, defaulting to today
        date_str = request.args.get('date')
        if date_str:
            try:
                report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                report_date = date.today()
        else:
            report_date = date.today()
            
        # Load orders for selected date
        completed_orders = load_completed_orders(report_date)
        
        return jsonify({
            'success': True,
            'date': report_date.isoformat(),
            'formatted_date': report_date.strftime('%d/%m/%Y'),
            'orders': completed_orders
        })
    except Exception as e:
        logger.exception(f"Error exporting report: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/connection/test', methods=['GET'])
def test_connection():
    """API endpoint to test the database connection."""
    try:
        is_success, message, diagnostics = db.test_connection()
        data_cache['connection_status']['diagnostics'] = diagnostics
        data_cache['connection_status']['last_check'] = datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
        
        if is_success:
            data_cache['connection_status']['status'] = 'connected'
        else:
            data_cache['connection_status']['status'] = 'disconnected'
        
        # Include local hostname and IP for debugging
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            diagnostics['client_hostname'] = hostname
            diagnostics['client_ip'] = local_ip
        except:
            pass
        
        return jsonify({
            'success': is_success,
            'message': message,
            'diagnostics': diagnostics,
            'timestamp': datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
        })
    except Exception as e:
        logger.exception(f"Error testing connection: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error testing connection: {str(e)}",
            'timestamp': datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
        }), 500

@app.route('/api/connection/toggle-offline', methods=['POST'])
def toggle_offline_mode():
    """API endpoint to toggle offline mode."""
    global OFFLINE_MODE
    try:
        OFFLINE_MODE = not OFFLINE_MODE
        return jsonify({
            'success': True,
            'offline_mode': OFFLINE_MODE,
            'message': f"Offline mode {'enabled' if OFFLINE_MODE else 'disabled'}"
        })
    except Exception as e:
        logger.exception(f"Error toggling offline mode: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@app.route('/diagnostics')
def diagnostics_page():
    """Render the diagnostics page."""
    # Test connection
    is_connected, message, conn_diagnostics = db.test_connection()
    
    # Get database schema information
    tables, tables_error = db_explorer.list_tables()
    schemas, schemas_error = db_explorer.list_schemas()
    
    # Check specific tables
    table_checks = []
    tables_to_check = ['Ocorrencias', 'Usuarios', 'Clientes', 'Produtos', 'Tipos_Ocorrencia']
    
    for table in tables_to_check:
        exists, error = db_explorer.table_exists(table)
        if error:
            table_checks.append({
                'table': table,
                'exists': False,
                'error': error
            })
        else:
            table_checks.append({
                'table': table,
                'exists': exists,
                'error': None
            })
            
            # If table exists, get columns
            if exists:
                columns, columns_error = db_explorer.list_columns(table)
                table_checks[-1]['columns'] = columns
                table_checks[-1]['columns_error'] = columns_error
    
    # Look for similar tables for Ocorrencias
    similar_tables, similar_error = db_explorer.search_similar_tables('Ocorrencia')
    
    # Get connection error message if any
    error_message = data_cache['connection_status'].get('error_message')
    
    return render_template('diagnostics.html',
                          is_connected=is_connected,
                          connection_message=message,
                          connection_diagnostics=conn_diagnostics,
                          tables=tables,
                          tables_error=tables_error,
                          schemas=schemas,
                          schemas_error=schemas_error,
                          table_checks=table_checks,
                          similar_tables=similar_tables,
                          similar_error=similar_error,
                          error_message=error_message,
                          db_schema=DB_SCHEMA,
                          db_server=DB_SERVER,
                          db_database=DB_DATABASE)

@app.route('/api/db/explore', methods=['GET'])
def api_explore_db():
    """API endpoint to explore database tables and schemas."""
    try:
        tables, tables_error = db_explorer.list_tables()
        schemas, schemas_error = db_explorer.list_schemas()
        
        return jsonify({
            'success': not (tables_error or schemas_error),
            'tables': tables,
            'schemas': schemas,
            'tables_error': tables_error,
            'schemas_error': schemas_error
        })
    except Exception as e:
        logger.exception(f"Error exploring database: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/db/table/<table_name>', methods=['GET'])
def api_table_details(table_name):
    """API endpoint to get table details."""
    schema_name = request.args.get('schema')
    try:
        # Check if table exists
        exists, error = db_explorer.table_exists(table_name, schema_name)
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 500
        
        if not exists:
            return jsonify({
                'success': False,
                'error': f"Table '{table_name}' does not exist"
            }), 404
        
        # Get table columns
        columns, columns_error = db_explorer.list_columns(table_name, schema_name)
        
        if columns_error:
            return jsonify({
                'success': False,
                'error': columns_error
            }), 500
        
        return jsonify({
            'success': True,
            'table_name': table_name,
            'schema_name': schema_name,
            'columns': columns
        })
    except Exception as e:
        logger.exception(f"Error getting table details: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/db/similar/<partial_name>', methods=['GET'])
def api_similar_tables(partial_name):
    """API endpoint to find similar table names."""
    try:
        tables, error = db_explorer.search_similar_tables(partial_name)
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 500
        
        return jsonify({
            'success': True,
            'partial_name': partial_name,
            'tables': tables
        })
    except Exception as e:
        logger.exception(f"Error finding similar tables: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/products')
def products_page():
    """Render the products statistics page."""
    return render_template('products.html',
                          last_update=data_cache['last_update'],
                          is_cache=data_cache['is_cache'],
                          connection_status=data_cache['connection_status']['status'],
                          offline_mode=OFFLINE_MODE,
                          now=datetime.now())

@scheduler.task('interval', id='refresh_data', seconds=180)  # Changed from 300 to 180 for 3 minute refresh
def scheduled_refresh():
    """Scheduled task to refresh data every 3 minutes."""
    with app.app_context():
        get_pending_orders()
        logger.info(f"Data refreshed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def create_folders():
    """Create the necessary folders for static files and data."""
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('utils', exist_ok=True)
    os.makedirs('data', exist_ok=True)  # Ensure data directory exists

@app.route('/api/tracking/status')
def get_tracking_status():
    """API endpoint to check tracking status"""
    return jsonify({
        'success': True,
        'tracking_count': len(COMPLETION_TRACKING['client_products']),
        'last_cleanup': COMPLETION_TRACKING['last_cleanup'].isoformat(),
        'persisted_to_disk': COMPLETION_TRACKING['persisted_to_disk'],
        'loaded_from_disk': COMPLETION_TRACKING['loaded_from_disk'],
    })

@app.route('/api/tracking/rebuild', methods=['POST'])
def rebuild_tracking():
    """API endpoint to rebuild tracking data"""
    try:
        rebuild_tracking_from_all_reports()
        return jsonify({
            'success': True,
            'tracking_count': len(COMPLETION_TRACKING['client_products']),
            'message': 'Rastreamento reconstruído com sucesso'
        })
    except Exception as e:
        logger.exception(f"Error rebuilding tracking: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Create necessary folders before starting the app
    create_folders()
    
    # Start the scheduler
    scheduler.init_app(app)
    scheduler.start()
    
    # Load the completion tracking data with improved persistence
    try:
        load_completion_tracking()
    except Exception as e:
        logger.error(f"Error loading completion tracking: {e}")
        # Continue anyway, this is not critical
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5003)
