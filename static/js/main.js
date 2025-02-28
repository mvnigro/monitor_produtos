// main.js - Functionality for the main dashboard page

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the page
    calculateTotalClients();
    calculateAverageWaitTime();
    initializeSearch();
    initializeRefreshButton();
    initializeMarkCompleteButtons();
    initializeAutoRefresh();
});

// Calculate and display total number of affected clients
function calculateTotalClients() {
    const totalClientsElement = document.getElementById('totalClients');
    let totalClients = 0;
    
    // Get all client counts from the table
    const clientButtons = document.querySelectorAll('[data-bs-toggle="modal"]');
    clientButtons.forEach(button => {
        const clientCount = parseInt(button.textContent.trim().split(' ')[0]);
        if (!isNaN(clientCount)) {
            totalClients += clientCount;
        }
    });
    
    totalClientsElement.textContent = totalClients;
}

// Calculate and display average wait time (mock data for now)
function calculateAverageWaitTime() {
    const avgWaitTimeElement = document.getElementById('avgWaitTime');
    
    // For now, we'll just display a mock average wait time
    // In a real implementation, this would calculate based on actual data
    avgWaitTimeElement.textContent = '2.5 dias';
}

// Initialize the search functionality
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;
    
    searchInput.addEventListener('keyup', function() {
        const searchTerm = this.value.toLowerCase();
        const tableRows = document.querySelectorAll('#productsTable tbody tr');
        
        tableRows.forEach(row => {
            const productName = row.cells[0].textContent.toLowerCase();
            const productCode = row.cells[1].textContent.toLowerCase();
            
            if (productName.includes(searchTerm) || productCode.includes(searchTerm)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
}

// Initialize the refresh button
function initializeRefreshButton() {
    const refreshBtn = document.getElementById('refreshBtn');
    if (!refreshBtn) return;
    
    refreshBtn.addEventListener('click', function() {
        // Add spinning animation to the refresh icon
        const icon = this.querySelector('i');
        icon.classList.add('rotating');
        
        // Fetch updated data from the API
        fetch('/api/pending-orders')
            .then(response => response.json())
            .then(data => {
                // Reload the page to show the updated data
                window.location.reload();
            })
            .catch(error => {
                console.error('Error refreshing data:', error);
                alert('Erro ao atualizar os dados. Por favor, tente novamente.');
            })
            .finally(() => {
                // Remove the spinning animation
                icon.classList.remove('rotating');
            });
    });
}

// Initialize the mark complete buttons
function initializeMarkCompleteButtons() {
    // For product-level completion
    const markCompleteButtons = document.querySelectorAll('.mark-complete');
    markCompleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            const productCode = this.getAttribute('data-product-code');
            const clients = JSON.parse(this.getAttribute('data-clients'));
            
            if (confirm(`Marcar produto ${productCode} como concluído para todos os ${clients.length} cliente(s)?`)) {
                markOrderComplete(productCode, clients);
            }
        });
    });
    
    // For client-level completion
    const markClientCompleteButtons = document.querySelectorAll('.mark-client-complete');
    markClientCompleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            const productCode = this.getAttribute('data-product-code');
            const clientName = this.getAttribute('data-client-name');
            
            if (confirm(`Marcar produto ${productCode} como concluído para o cliente ${clientName}?`)) {
                markOrderComplete(productCode, [clientName]);
            }
        });
    });
}

// Initialize auto-refresh functionality
function initializeAutoRefresh() {
    // Set auto-refresh interval to 3 minutes (180000 milliseconds)
    setInterval(function() {
        // Fetch updated data from the API
        fetch('/api/pending-orders')
            .then(response => response.json())
            .then(data => {
                // Reload the page to show the updated data
                window.location.reload();
            })
            .catch(error => {
                console.error('Error auto-refreshing data:', error);
            });
    }, 180000);
}

// Mark an order as complete
function markOrderComplete(productCode, clients) {
    // Show loading state
    const loadingSpinner = document.createElement('span');
    loadingSpinner.className = 'loading-spinner';
    
    // Get product name from the table
    let productName = '';
    const tableRows = document.querySelectorAll('#productsTable tbody tr');
    tableRows.forEach(row => {
        if (row.cells[1].textContent.includes(productCode)) {
            productName = row.cells[0].textContent.trim();
        }
    });
    
    // Get the current user name or show a selection dialog
    let completedBy = '';
    
    // Define the list of employees
    const employees = ['Richard', 'Cassio', 'Matheus', 'Marlon'];
    
    // Create and show a modal to select the employee
    const employeeModal = document.createElement('div');
    employeeModal.className = 'modal fade';
    employeeModal.id = 'employeeSelectionModal';
    employeeModal.setAttribute('tabindex', '-1');
    employeeModal.setAttribute('aria-hidden', 'true');
    
    employeeModal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Selecione o Funcionário</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="list-group">
                        ${employees.map(emp => `
                            <button type="button" class="list-group-item list-group-item-action employee-select" data-employee="${emp}">
                                <i class="bi bi-person"></i> ${emp}
                            </button>
                        `).join('')}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Append the modal to the body
    document.body.appendChild(employeeModal);
    
    // Initialize the Bootstrap modal
    const bsModal = new bootstrap.Modal(employeeModal);
    
    // Function to handle employee selection
    const selectEmployee = (employee) => {
        completedBy = employee;
        bsModal.hide();
        
        // Continue with the order completion process
        completeOrderWithEmployee(productCode, clients, completedBy);
    };
    
    // Add event listeners to the employee selection buttons
    employeeModal.querySelectorAll('.employee-select').forEach(button => {
        button.addEventListener('click', () => {
            selectEmployee(button.getAttribute('data-employee'));
        });
    });
    
    // Show the modal
    bsModal.show();
    
    // Return early as we'll continue after employee selection
    return;
}

// Complete order after employee selection
function completeOrderWithEmployee(productCode, clients, completedBy) {
    // Get product name from the table
    let productName = '';
    const tableRows = document.querySelectorAll('#productsTable tbody tr');
    tableRows.forEach(row => {
        if (row.cells[1].textContent.includes(productCode)) {
            productName = row.cells[0].textContent.trim();
        }
    });
    
    // For single client completion
    if (clients.length === 1) {
        const clientName = clients[0];
        
        // Send the completion request to the API
        fetch('/api/complete-order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                product_code: productCode,
                product_name: productName,
                client_name: clientName,
                completed_by: completedBy,
                separador: 'N/A'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload the page to reflect the changes
                window.location.reload();
            } else {
                alert('Erro ao marcar como concluído: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error marking as complete:', error);
            alert('Erro ao marcar como concluído. Por favor, tente novamente.');
        });
    } else {
        // This is a batch operation - we need to handle each client separately
        // Create a promise for each client
        const promises = clients.map(clientName => {
            return fetch('/api/complete-order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    product_code: productCode,
                    product_name: productName,
                    client_name: clientName,
                    completed_by: completedBy,
                    separador: 'N/A'
                })
            }).then(response => response.json());
        });
        
        // Wait for all requests to complete
        Promise.all(promises)
            .then(results => {
                // Check if all operations were successful
                const allSuccessful = results.every(result => result.success);
                if (allSuccessful) {
                    window.location.reload();
                } else {
                    const errors = results.filter(result => !result.success)
                        .map(result => result.error)
                        .join(', ');
                    alert('Alguns pedidos não puderam ser concluídos: ' + errors);
                }
            })
            .catch(error => {
                console.error('Error marking as complete:', error);
                alert('Erro ao marcar como concluído. Por favor, tente novamente.');
            });
    }
}

// Add a CSS class for the rotation animation
document.head.insertAdjacentHTML('beforeend', `
    <style>
        .rotating {
            animation: rotate 1s linear infinite;
        }
        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    </style>
`);