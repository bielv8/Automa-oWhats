/**
 * WhatsApp Automation System - Main JavaScript File
 * Handles client-side functionality and interactions
 */

// Global variables
let connectionCheckInterval;
let lastConnectionStatus = null;

// Initialize application when DOM is ready
$(document).ready(function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    // Initialize components
    initializeDataTables();
    initializeConnectionMonitoring();
    initializeFormValidations();
    initializeEventHandlers();
    initializeTooltips();
    
    // Auto-save form data to localStorage
    enableAutoSave();
    
    console.log('WhatsApp Automation System initialized');
}

/**
 * Initialize DataTables for all tables
 */
function initializeDataTables() {
    // Initialize contacts table if it exists
    if ($('#contactsTable').length) {
        $('#contactsTable').DataTable({
            "paging": false,
            "searching": false,
            "info": false,
            "ordering": true,
            "order": [[1, "asc"]], // Sort by name
            "columnDefs": [
                { "orderable": false, "targets": [0, 6] }, // Checkbox and actions columns
                { "width": "50px", "targets": 0 },
                { "width": "100px", "targets": 6 }
            ],
            "language": {
                "emptyTable": "Nenhum contato encontrado",
                "zeroRecords": "Nenhum registro encontrado"
            }
        });
    }

    // Initialize campaigns table if it exists
    if ($('#campaignsTable').length) {
        $('#campaignsTable').DataTable({
            "paging": true,
            "pageLength": 10,
            "searching": true,
            "info": true,
            "ordering": true,
            "order": [[6, "desc"]], // Sort by date created
            "columnDefs": [
                { "orderable": false, "targets": [7] }, // Actions column
                { "width": "100px", "targets": 7 }
            ],
            "language": {
                "search": "Buscar:",
                "lengthMenu": "Mostrar _MENU_ campanhas por página",
                "info": "Mostrando _START_ a _END_ de _TOTAL_ campanhas",
                "infoEmpty": "Nenhuma campanha encontrada",
                "infoFiltered": "(filtrado de _MAX_ campanhas)",
                "paginate": {
                    "first": "Primeira",
                    "last": "Última",
                    "next": "Próxima",
                    "previous": "Anterior"
                }
            }
        });
    }

    // Initialize history table if it exists
    if ($('#historyTable').length) {
        $('#historyTable').DataTable({
            "paging": true,
            "pageLength": 25,
            "searching": true,
            "info": true,
            "ordering": true,
            "order": [[0, "desc"]], // Sort by timestamp
            "language": {
                "search": "Buscar:",
                "lengthMenu": "Mostrar _MENU_ registros por página",
                "info": "Mostrando _START_ a _END_ de _TOTAL_ registros",
                "paginate": {
                    "next": "Próxima",
                    "previous": "Anterior"
                }
            }
        });
    }
}

/**
 * Initialize connection monitoring
 */
function initializeConnectionMonitoring() {
    // Check connection status immediately
    checkConnection();
    
    // Set up periodic connection checking (every 30 seconds)
    connectionCheckInterval = setInterval(checkConnection, 30000);
    
    // Check connection when window becomes visible
    $(document).on('visibilitychange', function() {
        if (!document.hidden) {
            checkConnection();
        }
    });
}

/**
 * Check WhatsApp Web connection status
 */
function checkConnection() {
    $.ajax({
        url: '/connection/check',
        type: 'GET',
        timeout: 10000,
        success: function(data) {
            updateConnectionStatus(data);
        },
        error: function(xhr, status, error) {
            console.error('Error checking connection:', error);
            updateConnectionStatus({
                status: 'error',
                message: 'Erro ao verificar conexão'
            });
        }
    });
}

/**
 * Update connection status in UI
 */
function updateConnectionStatus(data) {
    const statusBadge = $('#connection-status');
    const connectionCard = $('#connection-card');
    const connectionText = $('#connection-text');
    
    if (!statusBadge.length) return;
    
    // Update status badge in navbar
    if (data.status === 'connected') {
        statusBadge.removeClass('bg-danger bg-secondary bg-warning')
                   .addClass('bg-success')
                   .html('<i class="fas fa-circle me-1"></i>Conectado');
                   
        if (connectionCard.length) {
            connectionCard.removeClass('bg-danger bg-secondary bg-warning')
                         .addClass('bg-success');
        }
        
        if (connectionText.length) {
            connectionText.text('Conectado');
        }
        
        // Show phone number and profile name if available
        if (data.phone_number && $('.connection-details').length) {
            $('.connection-details').html(`
                <small class="text-muted d-block">
                    ${data.phone_number}<br>
                    ${data.profile_name || 'WhatsApp Web'}
                </small>
            `);
        }
        
    } else if (data.status === 'disconnected') {
        statusBadge.removeClass('bg-success bg-secondary bg-warning')
                   .addClass('bg-danger')
                   .html('<i class="fas fa-circle me-1"></i>Desconectado');
                   
        if (connectionCard.length) {
            connectionCard.removeClass('bg-success bg-secondary bg-warning')
                         .addClass('bg-danger');
        }
        
        if (connectionText.length) {
            connectionText.text('Desconectado');
        }
        
    } else {
        statusBadge.removeClass('bg-success bg-danger bg-warning')
                   .addClass('bg-secondary')
                   .html('<i class="fas fa-circle me-1"></i>Verificando...');
                   
        if (connectionCard.length) {
            connectionCard.removeClass('bg-success bg-danger bg-warning')
                         .addClass('bg-secondary');
        }
        
        if (connectionText.length) {
            connectionText.text('Verificando...');
        }
    }
    
    // Store last status for comparison
    lastConnectionStatus = data.status;
    
    // Show notification if status changed significantly
    if (data.status === 'connected' && lastConnectionStatus === 'disconnected') {
        showNotification('WhatsApp Web conectado com sucesso!', 'success');
    } else if (data.status === 'disconnected' && lastConnectionStatus === 'connected') {
        showNotification('WhatsApp Web foi desconectado', 'warning');
    }
}

/**
 * Initialize form validations
 */
function initializeFormValidations() {
    // Phone number validation
    $('input[type="tel"], input[name="phone"]').on('input', function() {
        const phone = $(this).val();
        const isValid = validatePhoneNumber(phone);
        
        if (phone.length > 0) {
            $(this).toggleClass('is-valid', isValid)
                   .toggleClass('is-invalid', !isValid);
                   
            // Show/hide validation feedback
            const feedback = $(this).next('.invalid-feedback');
            if (!isValid && feedback.length === 0) {
                $(this).after('<div class="invalid-feedback">Número de telefone inválido</div>');
            } else if (isValid) {
                feedback.remove();
            }
        } else {
            $(this).removeClass('is-valid is-invalid');
            $(this).next('.invalid-feedback').remove();
        }
    });

    // Email validation
    $('input[type="email"]').on('input', function() {
        const email = $(this).val();
        const isValid = email === '' || validateEmail(email);
        
        if (email.length > 0) {
            $(this).toggleClass('is-valid', isValid)
                   .toggleClass('is-invalid', !isValid);
        } else {
            $(this).removeClass('is-valid is-invalid');
        }
    });

    // Template content validation
    $('#content').on('input', function() {
        const content = $(this).val();
        if (content.length > 0) {
            updateTemplatePreview();
            $(this).addClass('is-valid');
        } else {
            $(this).removeClass('is-valid');
        }
    });

    // Form submission validation
    $('form').on('submit', function(e) {
        const form = $(this)[0];
        if (!form.checkValidity()) {
            e.preventDefault();
            e.stopPropagation();
            
            // Focus on first invalid field
            const firstInvalid = $(this).find(':invalid').first();
            if (firstInvalid.length) {
                firstInvalid.focus();
                showNotification('Por favor, corrija os campos obrigatórios', 'error');
            }
        }
        $(this).addClass('was-validated');
    });
}

/**
 * Initialize event handlers
 */
function initializeEventHandlers() {
    // Contact selection handlers
    initializeContactSelection();
    
    // Template preview handlers
    initializeTemplatePreview();
    
    // Campaign handlers
    initializeCampaignHandlers();
    
    // File upload handlers
    initializeFileUpload();
    
    // Search functionality
    initializeSearch();
    
    // Modal handlers
    initializeModalHandlers();
}

/**
 * Initialize contact selection functionality
 */
function initializeContactSelection() {
    // Select all checkbox functionality
    $(document).on('change', '#selectAll, #selectAllContacts', function() {
        const isChecked = $(this).is(':checked');
        $('.contact-checkbox').prop('checked', isChecked);
        updateSelectedCount();
        updateBulkActions();
    });

    // Individual contact checkbox functionality
    $(document).on('change', '.contact-checkbox', function() {
        updateSelectedCount();
        updateBulkActions();
        
        // Update select all checkbox state
        const totalCheckboxes = $('.contact-checkbox').length;
        const checkedCheckboxes = $('.contact-checkbox:checked').length;
        
        const selectAllCheckbox = $('#selectAll, #selectAllContacts');
        selectAllCheckbox.prop('indeterminate', checkedCheckboxes > 0 && checkedCheckboxes < totalCheckboxes);
        selectAllCheckbox.prop('checked', checkedCheckboxes === totalCheckboxes);
    });

    // Bulk actions
    $(document).on('click', '#bulkActionsBtn', function() {
        const selectedIds = getSelectedContactIds();
        if (selectedIds.length > 0) {
            const params = selectedIds.map(id => `contact_ids=${id}`).join('&');
            window.location.href = `/campaigns?${params}`;
        }
    });
}

/**
 * Update selected contact count display
 */
function updateSelectedCount() {
    const count = $('.contact-checkbox:checked').length;
    $('#selectedCount').text(count);
    
    // Update bulk actions button text
    const bulkBtn = $('#bulkActionsBtn');
    if (bulkBtn.length) {
        if (count > 0) {
            bulkBtn.html(`<i class="fas fa-paper-plane me-2"></i>Criar Campanha com ${count} Selecionados`);
        } else {
            bulkBtn.html('<i class="fas fa-paper-plane me-2"></i>Criar Campanha com Selecionados');
        }
    }
}

/**
 * Update bulk actions button state
 */
function updateBulkActions() {
    const selectedCount = $('.contact-checkbox:checked').length;
    $('#bulkActionsBtn').prop('disabled', selectedCount === 0);
}

/**
 * Get selected contact IDs
 */
function getSelectedContactIds() {
    return $('.contact-checkbox:checked').map(function() {
        return this.value;
    }).get();
}

/**
 * Initialize template preview functionality
 */
function initializeTemplatePreview() {
    // Real-time preview while typing
    $(document).on('input', '#content', function() {
        updateTemplatePreview();
    });
}

/**
 * Update template preview with sample data
 */
function updateTemplatePreview() {
    const content = $('#content').val();
    const previewElement = $('#messagePreview, #templatePreview');
    
    if (!previewElement.length) return;
    
    if (content.trim() === '') {
        previewElement.html('<em class="text-muted">Digite o conteúdo para ver o preview...</em>');
        return;
    }
    
    // Replace variables with sample data for preview
    let preview = content
        .replace(/\{\{nome\}\}/g, '<span class="text-primary fw-bold">João Silva</span>')
        .replace(/\{\{telefone\}\}/g, '<span class="text-info">11 99999-9999</span>')
        .replace(/\{\{email\}\}/g, '<span class="text-info">joao@email.com</span>')
        .replace(/\{\{empresa\}\}/g, '<span class="text-warning">Empresa ABC</span>');
    
    // Convert line breaks to HTML
    preview = preview.replace(/\n/g, '<br>');
    
    previewElement.html(preview);
}

/**
 * Initialize campaign handlers
 */
function initializeCampaignHandlers() {
    // Campaign form validation
    $(document).on('submit', '#campaignForm', function(e) {
        const selectedContacts = $('.contact-checkbox:checked').length;
        const templateSelected = $('#template_id').val();
        
        if (selectedContacts === 0) {
            e.preventDefault();
            showNotification('Selecione pelo menos um contato para a campanha', 'error');
            return false;
        }
        
        if (!templateSelected) {
            e.preventDefault();
            showNotification('Selecione um template para a campanha', 'error');
            return false;
        }
    });

    // Start campaign confirmation
    $(document).on('click', '.start-campaign-btn', function(e) {
        e.preventDefault();
        const campaignId = $(this).data('campaign-id');
        const campaignName = $(this).data('campaign-name');
        
        if (confirm(`Iniciar a campanha "${campaignName}"? Esta ação não pode ser desfeita.`)) {
            startCampaign(campaignId);
        }
    });
}

/**
 * Start a campaign
 */
function startCampaign(campaignId) {
    const button = $(`.start-campaign-btn[data-campaign-id="${campaignId}"]`);
    const originalHtml = button.html();
    
    // Show loading state
    button.prop('disabled', true)
          .html('<i class="fas fa-spinner fa-spin me-2"></i>Iniciando...');
    
    $.ajax({
        url: `/campaigns/${campaignId}/start`,
        type: 'GET',
        success: function(response) {
            showNotification('Campanha iniciada com sucesso!', 'success');
            setTimeout(() => {
                location.reload();
            }, 2000);
        },
        error: function(xhr, status, error) {
            console.error('Error starting campaign:', error);
            showNotification('Erro ao iniciar campanha', 'error');
            
            // Reset button state
            button.prop('disabled', false)
                  .html(originalHtml);
        }
    });
}

/**
 * Initialize file upload functionality
 */
function initializeFileUpload() {
    // CSV file upload validation
    $('input[type="file"][accept=".csv"]').on('change', function() {
        const file = this.files[0];
        if (file) {
            if (!file.name.toLowerCase().endsWith('.csv')) {
                showNotification('Por favor, selecione um arquivo CSV válido', 'error');
                $(this).val('');
                return;
            }
            
            if (file.size > 5 * 1024 * 1024) { // 5MB limit
                showNotification('Arquivo muito grande. Tamanho máximo: 5MB', 'error');
                $(this).val('');
                return;
            }
            
            // Show file info
            const fileInfo = `Arquivo selecionado: ${file.name} (${formatFileSize(file.size)})`;
            $(this).next('.file-info').remove();
            $(this).after(`<small class="file-info text-muted d-block mt-1">${fileInfo}</small>`);
        }
    });

    // Drag and drop functionality
    $('.file-drop-area').on('dragover', function(e) {
        e.preventDefault();
        $(this).addClass('dragover');
    }).on('dragleave', function(e) {
        e.preventDefault();
        $(this).removeClass('dragover');
    }).on('drop', function(e) {
        e.preventDefault();
        $(this).removeClass('dragover');
        
        const files = e.originalEvent.dataTransfer.files;
        if (files.length > 0) {
            const fileInput = $(this).find('input[type="file"]')[0];
            fileInput.files = files;
            $(fileInput).trigger('change');
        }
    });
}

/**
 * Initialize search functionality
 */
function initializeSearch() {
    // Real-time search with debouncing
    let searchTimeout;
    
    $(document).on('input', '.search-input', function() {
        const searchTerm = $(this).val();
        const targetTable = $(this).data('target') || 'table';
        
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            performSearch(searchTerm, targetTable);
        }, 300);
    });
    
    // Search form submission
    $(document).on('submit', '.search-form', function(e) {
        e.preventDefault();
        const searchTerm = $(this).find('.search-input').val();
        const currentUrl = new URL(window.location);
        
        if (searchTerm) {
            currentUrl.searchParams.set('search', searchTerm);
        } else {
            currentUrl.searchParams.delete('search');
        }
        
        window.location.href = currentUrl.toString();
    });
    
    // Clear search
    $(document).on('click', '.clear-search', function() {
        $('.search-input').val('');
        const currentUrl = new URL(window.location);
        currentUrl.searchParams.delete('search');
        window.location.href = currentUrl.toString();
    });
}

/**
 * Perform client-side search
 */
function performSearch(searchTerm, targetTable) {
    const table = $(targetTable);
    if (!table.length) return;
    
    const rows = table.find('tbody tr');
    
    if (!searchTerm) {
        rows.show();
        return;
    }
    
    rows.each(function() {
        const text = $(this).text().toLowerCase();
        const matches = text.includes(searchTerm.toLowerCase());
        $(this).toggle(matches);
    });
}

/**
 * Initialize modal handlers
 */
function initializeModalHandlers() {
    // Reset forms when modals are closed
    $('.modal').on('hidden.bs.modal', function() {
        const form = $(this).find('form');
        if (form.length) {
            form[0].reset();
            form.removeClass('was-validated');
            form.find('.is-valid, .is-invalid').removeClass('is-valid is-invalid');
            form.find('.invalid-feedback').remove();
        }
    });
    
    // Auto-focus first input when modal opens
    $('.modal').on('shown.bs.modal', function() {
        $(this).find('input:text, input:email, input:tel, textarea, select').first().focus();
    });
}

/**
 * Initialize tooltips
 */
function initializeTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Enable auto-save functionality
 */
function enableAutoSave() {
    // Save form data to localStorage
    $('input, textarea, select').on('input change', function() {
        const formId = $(this).closest('form').attr('id');
        if (formId && $(this).attr('name')) {
            const key = `autosave_${formId}_${$(this).attr('name')}`;
            localStorage.setItem(key, $(this).val());
        }
    });
    
    // Restore form data from localStorage
    $('form[id]').each(function() {
        const formId = $(this).attr('id');
        $(this).find('input, textarea, select').each(function() {
            const fieldName = $(this).attr('name');
            if (fieldName) {
                const key = `autosave_${formId}_${fieldName}`;
                const savedValue = localStorage.getItem(key);
                if (savedValue && !$(this).val()) {
                    $(this).val(savedValue);
                }
            }
        });
    });
    
    // Clear auto-saved data when form is successfully submitted
    $('form').on('submit', function() {
        const formId = $(this).attr('id');
        if (formId) {
            $(this).find('input, textarea, select').each(function() {
                const fieldName = $(this).attr('name');
                if (fieldName) {
                    const key = `autosave_${formId}_${fieldName}`;
                    localStorage.removeItem(key);
                }
            });
        }
    });
}

/**
 * Utility Functions
 */

/**
 * Validate phone number
 */
function validatePhoneNumber(phone) {
    if (!phone) return false;
    
    // Remove all non-digit characters
    const cleaned = phone.replace(/\D/g, '');
    
    // Check if it's a valid Brazilian phone number (10-15 digits)
    return cleaned.length >= 10 && cleaned.length <= 15;
}

/**
 * Validate email address
 */
function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Show notification
 */
function showNotification(message, type = 'info', duration = 5000) {
    const alertClass = type === 'error' ? 'danger' : type;
    const icon = {
        success: 'fas fa-check-circle',
        error: 'fas fa-times-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    }[type] || 'fas fa-info-circle';
    
    const alertHtml = `
        <div class="alert alert-${alertClass} alert-dismissible fade show notification-alert" role="alert">
            <i class="${icon} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Remove existing notifications
    $('.notification-alert').remove();
    
    // Add new notification to top of container
    $('.container').first().prepend(alertHtml);
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            $('.notification-alert').fadeOut(() => {
                $('.notification-alert').remove();
            });
        }, duration);
    }
}

/**
 * Show loading state
 */
function showLoading(element, text = 'Carregando...') {
    const $el = $(element);
    const originalHtml = $el.html();
    
    $el.data('original-html', originalHtml)
       .prop('disabled', true)
       .html(`<i class="fas fa-spinner fa-spin me-2"></i>${text}`);
}

/**
 * Hide loading state
 */
function hideLoading(element) {
    const $el = $(element);
    const originalHtml = $el.data('original-html');
    
    if (originalHtml) {
        $el.prop('disabled', false)
           .html(originalHtml)
           .removeData('original-html');
    }
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Export functionality
 */
function exportData(type, format = 'csv') {
    const url = `/${type}/export?format=${format}`;
    window.open(url, '_blank');
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Texto copiado para a área de transferência', 'success', 2000);
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
            document.execCommand('copy');
            showNotification('Texto copiado para a área de transferência', 'success', 2000);
        } catch (err) {
            showNotification('Erro ao copiar texto', 'error');
        }
        document.body.removeChild(textArea);
    }
}

/**
 * Check if user is online
 */
function checkOnlineStatus() {
    if (navigator.onLine) {
        $('.offline-indicator').hide();
        // Resume connection monitoring if it was paused
        if (!connectionCheckInterval) {
            initializeConnectionMonitoring();
        }
    } else {
        $('.offline-indicator').show();
        // Pause connection monitoring when offline
        if (connectionCheckInterval) {
            clearInterval(connectionCheckInterval);
            connectionCheckInterval = null;
        }
    }
}

// Handle online/offline events
window.addEventListener('online', checkOnlineStatus);
window.addEventListener('offline', checkOnlineStatus);

// Cleanup on page unload
$(window).on('beforeunload', function() {
    // Clear intervals
    if (connectionCheckInterval) {
        clearInterval(connectionCheckInterval);
    }
    
    // Clean up any pending AJAX requests
    $.ajaxSetup({
        beforeSend: function(xhr) {
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        }
    });
});

// Global error handler for AJAX requests
$(document).ajaxError(function(event, xhr, settings, error) {
    if (xhr.status === 0) {
        // Network error or request was cancelled
        showNotification('Erro de conexão. Verifique sua internet.', 'error');
    } else if (xhr.status === 500) {
        showNotification('Erro interno do servidor. Tente novamente.', 'error');
    } else if (xhr.status === 404) {
        showNotification('Recurso não encontrado.', 'error');
    } else {
        showNotification(`Erro: ${xhr.status} - ${error}`, 'error');
    }
});

// Export main functions for global access
window.WhatsAppAutomation = {
    checkConnection,
    updateConnectionStatus,
    showNotification,
    showLoading,
    hideLoading,
    formatDate,
    copyToClipboard,
    exportData
};

console.log('WhatsApp Automation System JavaScript loaded successfully');
