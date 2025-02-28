// products.js - Functionality for the products statistics page

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the page
    initializeRefreshButton();
    fetchProductStats();
    initializeAutoRefresh();
});

// Initialize the refresh button
function initializeRefreshButton() {
    const refreshBtn = document.getElementById('refreshBtn');
    if (!refreshBtn) return;
    
    refreshBtn.addEventListener('click', function() {
        // Add spinning animation to the refresh icon
        const icon = this.querySelector('i');
        icon.classList.add('rotating');
        
        // Fetch updated data from the API
        fetch('/api/stats')
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

// Fetch product statistics from the API
function fetchProductStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            if (data.stats) {
                updateProductsChart(data.stats);
                updateStatsCards(data.stats);
                updateTopProductsTable(data.stats);
                updateTrendChart(data.stats);
            }
        })
        .catch(error => {
            console.error('Error fetching stats:', error);
            // Show error message on the page
            document.querySelectorAll('.chart-container').forEach(container => {
                container.innerHTML = '<div class="alert alert-danger">Erro ao carregar dados. Por favor, tente novamente.</div>';
            });
        });
}

// Initialize auto-refresh functionality
function initializeAutoRefresh() {
    // Set auto-refresh interval to 3 minutes (180000 milliseconds)
    setInterval(function() {
        // Fetch updated data from the API
        fetch('/api/stats')
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

// Update the main products chart
function updateProductsChart(stats) {
    const ctx = document.getElementById('productsChart').getContext('2d');
    
    // Get the top 10 products by client count
    const labels = stats.product_labels.slice(0, 10);
    const data = stats.product_counts.slice(0, 10);
    
    // Create gradient for bars
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(0, 88, 81, 0.8)');
    gradient.addColorStop(1, 'rgba(0, 88, 81, 0.2)');
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Número de Clientes',
                data: data,
                backgroundColor: gradient,
                borderColor: 'rgba(0, 88, 81, 1)',
                borderWidth: 1,
                borderRadius: 4,
                barThickness: 30,
                maxBarThickness: 40
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    padding: 10,
                    titleFont: {
                        size: 14
                    },
                    bodyFont: {
                        size: 13
                    },
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y} cliente(s)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Número de Clientes',
                        font: {
                            weight: 'bold'
                        }
                    },
                    ticks: {
                        precision: 0
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Produtos',
                        font: {
                            weight: 'bold'
                        }
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

// Update the stats cards
function updateStatsCards(stats) {
    // Update total products
    const totalProducts = document.getElementById('totalProducts');
    if (totalProducts) {
        totalProducts.textContent = stats.product_labels.length;
    }
    
    // Update total clients
    const totalClients = document.getElementById('totalClients');
    if (totalClients) {
        const clientSum = stats.product_counts.reduce((a, b) => a + b, 0);
        totalClients.textContent = clientSum;
    }
    
    // Average wait time would be calculated from actual data
    // For now, we'll just use a placeholder
    const avgWaitTime = document.getElementById('avgWaitTime');
    if (avgWaitTime) {
        avgWaitTime.textContent = '2.5 dias';
    }
}

// Update the top products table
function updateTopProductsTable(stats) {
    const tableBody = document.getElementById('topProductsTableBody');
    if (!tableBody) return;
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    // Get the top 10 products
    const topProducts = [];
    for (let i = 0; i < Math.min(10, stats.product_labels.length); i++) {
        topProducts.push({
            name: stats.product_labels[i],
            count: stats.product_counts[i]
        });
    }
    
    // Sort by count (descending)
    topProducts.sort((a, b) => b.count - a.count);
    
    // Add rows to the table
    topProducts.forEach((product, index) => {
        const row = document.createElement('tr');
        
        // Extract product name and code
        const productParts = product.name.split('(');
        const productName = productParts[0].trim();
        const productCode = productParts[1] ? productParts[1].replace(')', '') : 'N/A';
        
        // Create row content
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${productName}</td>
            <td><span class="badge bg-secondary">${productCode}</span></td>
            <td><span class="badge bg-primary">${product.count}</span></td>
            <td>Hoje</td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // If no products, show a message
    if (topProducts.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="5" class="text-center">Nenhum produto em espera encontrado</td>';
        tableBody.appendChild(row);
    }
}

// Update the trend chart
function updateTrendChart(stats) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    
    // For now, we'll create a mock trend chart with random data
    // In a real implementation, this would use historical data
    
    // Get the top 5 products
    const topProducts = [];
    for (let i = 0; i < Math.min(5, stats.product_labels.length); i++) {
        const productParts = stats.product_labels[i].split('(');
        const productName = productParts[0].trim();
        topProducts.push(productName);
    }
    
    // Create mock data for the last 7 days
    const labels = [];
    const today = new Date();
    for (let i = 6; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(today.getDate() - i);
        labels.push(date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }));
    }
    
    // Create datasets for each product
    const datasets = [];
    const colors = ['#005851', '#dc3545', '#ffc107', '#198754', '#6610f2'];
    
    topProducts.forEach((product, index) => {
        // Generate random data for this product
        const data = [];
        for (let i = 0; i < 7; i++) {
            data.push(Math.floor(Math.random() * 10) + 1);
        }
        
        datasets.push({
            label: product,
            data: data,
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length] + '20',
            borderWidth: 2,
            fill: true,
            tension: 0.4
        });
    });
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false
                },
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Número de Clientes',
                        font: {
                            weight: 'bold'
                        }
                    },
                    ticks: {
                        precision: 0
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Data',
                        font: {
                            weight: 'bold'
                        }
                    }
                }
            }
        }
    });
}

// Add a CSS class for the rotation animation if not already added
if (!document.querySelector('style.products-js-styles')) {
    document.head.insertAdjacentHTML('beforeend', `
        <style class="products-js-styles">
            .rotating {
                animation: rotate 1s linear infinite;
            }
            @keyframes rotate {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
        </style>
    `);
}