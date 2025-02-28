import random
from datetime import datetime, timedelta

def get_mock_orders():
    """Generate mock pending orders for testing"""
    products = [
        {"name": "Paracetamol 500mg", "code": "P500"},
        {"name": "Ibuprofeno 600mg", "code": "I600"},
        {"name": "Dipirona 1g", "code": "D1000"},
        {"name": "Amoxicilina 500mg", "code": "A500"},
        {"name": "Loratadina 10mg", "code": "L10"},
        {"name": "Omeprazol 20mg", "code": "O20"},
        {"name": "Vitamina C 1g", "code": "VC1000"},
        {"name": "Complexo B", "code": "CB"}
    ]
    
    clients = [
        "Farmácia São João",
        "Drogaria Moderna",
        "Farmácia Popular",
        "Drogaria Saúde",
        "Farmácia Central",
        "Drogaria Bem Estar",
        "Farmácia Vida",
        "Drogaria Esperança"
    ]
    
    separadores = [
        "Carlos Silva",
        "Maria Oliveira",
        "João Santos",
        "Ana Pereira",
        "Pedro Costa"
    ]
    
    # Generate random orders
    orders = []
    used_combinations = set()  # To avoid duplicates
    
    # Generate between 5 and 15 products
    num_products = random.randint(5, 15)
    
    for _ in range(num_products):
        # Select a random product
        product = random.choice(products)
        product_name = f"{product['name']} ({product['code']})"
        product_code = product['code']
        
        # Generate between 1 and 5 clients for this product
        num_clients = random.randint(1, 5)
        product_clients = []
        client_details = []
        
        for _ in range(num_clients):
            client = random.choice(clients)
            separador = random.choice(separadores)
            
            # Avoid duplicate client-product combinations
            combination = f"{client}:{product_code}"
            if combination in used_combinations:
                continue
                
            used_combinations.add(combination)
            
            # Generate a random timestamp within the last 24 hours
            hours_ago = random.randint(1, 24)
            timestamp = (datetime.now() - timedelta(hours=hours_ago)).strftime('%d/%m/%Y, %H:%M:%S')
            
            # Add client to the list if not already there
            if client not in product_clients:
                product_clients.append(client)
                client_details.append({
                    'nome': client,
                    'data_ocorrencia': timestamp,
                    'separador': separador,
                    'texto_ocorrencia': f"Aguardando produto {product['name']}"
                })
        
        # Only add products that have clients
        if product_clients:
            orders.append({
                'produto': product_name,
                'codigo': product_code,
                'clientes': product_clients,
                'clientes_detalhes': client_details,
                'cliente': f"{len(product_clients)} cliente(s): {', '.join(product_clients)}",
                'tipo_ocorrencia': 'Espera por Produto',
                'status': 'Conferido',
                'data_ocorrencia': (datetime.now() - timedelta(hours=random.randint(1, 12))).strftime('%d/%m/%Y, %H:%M:%S')
            })
    
    # Sort by number of clients (descending)
    orders = sorted(orders, key=lambda x: len(x['clientes']), reverse=True)
    
    return orders

def get_mock_stats():
    """Generate mock statistics for testing"""
    # Generate between 5 and 10 products for stats
    num_products = random.randint(5, 10)
    
    product_labels = [
        f"Produto {i+1} (P{i+1})" for i in range(num_products)
    ]
    
    product_counts = [
        random.randint(1, 8) for _ in range(num_products)
    ]
    
    return {
        'product_labels': product_labels,
        'product_counts': product_counts
    }

def mark_mock_order_completed(client_name, product_code):
    """Simulate marking an order as completed in mock mode"""
    # In mock mode, we just return success
    return True, None