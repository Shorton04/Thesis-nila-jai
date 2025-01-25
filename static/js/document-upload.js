// static/js/document-upload.js

document.addEventListener('DOMContentLoaded', function() {
    // Single File Upload Handling
    const singleUploadForm = document.getElementById('singleUploadForm');
    const singleFileInput = document.getElementById('singleFileInput');
    const singleDropZone = singleFileInput.closest('.border-dashed');

    // Batch Upload Handling
    const batchUploadForm = document.getElementById('batchUploadForm');
    const batchFileInput = document.getElementById('batchFileInput');
    const batchDropZone = batchFileInput.closest('.border-dashed');
    const batchFileList = document.getElementById('batchFileList');

    // Drag and Drop Handlers
    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.add('border-indigo-500');
    }

    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.remove('border-indigo-500');
    }

    function handleDrop(e, fileInput) {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.remove('border-indigo-500');

        const files = e.dataTransfer.files;
        fileInput.files = files;

        if (fileInput === batchFileInput) {
            updateBatchFileList(files);
        }
    }

    // Add drag and drop listeners
    [singleDropZone, batchDropZone].forEach(dropZone => {
        dropZone.addEventListener('dragover', handleDragOver);
        dropZone.addEventListener('dragleave', handleDragLeave);
    });

    singleDropZone.addEventListener('drop', e => handleDrop(e, singleFileInput));
    batchDropZone.addEventListener('drop', e => handleDrop(e, batchFileInput));

    // Update batch file list
    function updateBatchFileList(files) {
        batchFileList.innerHTML = '';
        Array.from(files).forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'flex items-center justify-between p-2 bg-gray-50 rounded';
            fileItem.innerHTML = `
                <span class="text-sm text-gray-600">${file.name}</span>
                <span class="text-xs text-gray-500">${formatFileSize(file.size)}</span>
            `;
            batchFileList.appendChild(fileItem);
        });
    }

    // File size formatter
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Single file upload handler
    singleUploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const formData = new FormData(this);
        const submitButton = this.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.innerHTML = 'Uploading...';

        try {
            const response = await fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            });

            const result = await response.json();

            if (result.success) {
                if (result.extracted_data) {
                    // Handle form autofill
                    handleFormAutofill(result.extracted_data);
                }
                showNotification('Document uploaded successfully', 'success');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                showNotification(result.error || 'Upload failed', 'error');
            }
        } catch (error) {
            showNotification('Error uploading document', 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.innerHTML = 'Upload Document';
        }
    });

    // Batch upload handler
    batchUploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const formData = new FormData(this);
        const submitButton = this.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.innerHTML = 'Uploading...';

        try {
            const response = await fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            });

            const result = await response.json();

            if (result.success) {
                showNotification('Documents uploaded successfully', 'success');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                showNotification(result.error || 'Upload failed', 'error');
            }
        } catch (error) {
            showNotification('Error uploading documents', 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.innerHTML = 'Upload All Documents';
        }
    });
    

    // Form autofill handler
    function handleFormAutofill(data) {
        // Find form fields and populate them with extracted data
        Object.entries(data).forEach(([field, value]) => {
            const input = document.querySelector(`[name="${field}"]`);
            if (input) {
                input.value = value;
                // Trigger change event for any dependent validations
                input.dispatchEvent(new Event('change'));
                // Highlight the autofilled field
                highlightAutofillField(input);
            }
        });
    }

    // Highlight autofilled fields with a subtle animation
    function highlightAutofillField(element) {
        element.classList.add('bg-green-50', 'transition-colors');
        setTimeout(() => {
            element.classList.remove('bg-green-50');
        }, 2000);
    }

    // Notification system
    function showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 px-6 py-3 rounded-md shadow-lg transform transition-all duration-300 ${
            type === 'success' ? 'bg-green-500' : 'bg-red-500'
        } text-white`;

        notification.innerHTML = `
            <div class="flex items-center space-x-2">
                <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    ${type === 'success' 
                        ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>'
                        : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>'}
                </svg>
                <span>${message}</span>
            </div>
        `;

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.classList.add('translate-y-2', 'opacity-100');
        }, 100);

        // Remove after delay
        setTimeout(() => {
            notification.classList.remove('translate-y-2', 'opacity-100');
            notification.classList.add('-translate-y-2', 'opacity-0');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }

    // File validation
    function validateFile(file) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png'];
        const errors = [];

        if (file.size > maxSize) {
            errors.push(`File size exceeds 10MB limit (${formatFileSize(file.size)})`);
        }

        if (!allowedTypes.includes(file.type)) {
            errors.push('File type not supported. Please use PDF, JPG, or PNG files.');
        }

        return errors;
    }

    // File input change handlers
    singleFileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            const file = this.files[0];
            const errors = validateFile(file);

            if (errors.length > 0) {
                showNotification(errors[0], 'error');
                this.value = ''; // Clear the input
                return;
            }

            // Update the dropzone UI
            const fileInfo = this.closest('.border-dashed').querySelector('.text-gray-600');
            fileInfo.textContent = `Selected: ${file.name}`;
        }
    });

    batchFileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            const files = Array.from(this.files);
            const allErrors = [];

            files.forEach(file => {
                const errors = validateFile(file);
                if (errors.length > 0) {
                    allErrors.push(`${file.name}: ${errors[0]}`);
                }
            });

            if (allErrors.length > 0) {
                showNotification(`Some files are invalid: ${allErrors[0]}`, 'error');
                this.value = ''; // Clear the input
                batchFileList.innerHTML = '';
                return;
            }

            updateBatchFileList(this.files);
        }
    });

    // Progress tracking
    function updateUploadProgress(progressEvent, progressBar) {
        if (progressEvent.lengthComputable) {
            const percentComplete = (progressEvent.loaded / progressEvent.total) * 100;
            progressBar.style.width = percentComplete + '%';
            progressBar.textContent = Math.round(percentComplete) + '%';
        }
    }

    // Document preview
    function createDocumentPreview(file) {
        return new Promise((resolve) => {
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    resolve(e.target.result);
                };
                reader.readAsDataURL(file);
            } else if (file.type === 'application/pdf') {
                // For PDFs, we'll show a generic PDF icon
                resolve('/static/images/pdf-icon.svg');
            }
        });
    }

    // Keyboard accessibility
    function setupKeyboardAccessibility() {
        const dropZones = document.querySelectorAll('.border-dashed');
        dropZones.forEach(zone => {
            zone.setAttribute('tabindex', '0');
            zone.setAttribute('role', 'button');
            zone.setAttribute('aria-label', 'Drop zone for file upload');

            zone.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    zone.querySelector('input[type="file"]').click();
                }
            });
        });
    }

    // Initialize keyboard accessibility
    setupKeyboardAccessibility();

    // Error handling and retry mechanism
    async function uploadWithRetry(url, formData, maxRetries = 3) {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                if (attempt === maxRetries) {
                    throw error;
                }
                // Wait before retrying (exponential backoff)
                await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
            }
        }
    }

    // Initialize tooltips for UI elements
    function initializeTooltips() {
        const tooltips = document.querySelectorAll('[data-tooltip]');
        tooltips.forEach(element => {
            element.addEventListener('mouseenter', (e) => {
                const tooltip = document.createElement('div');
                tooltip.className = 'absolute bg-gray-900 text-white px-2 py-1 rounded text-sm z-50';
                tooltip.textContent = e.target.dataset.tooltip;
                document.body.appendChild(tooltip);

                const rect = e.target.getBoundingClientRect();
                tooltip.style.top = `${rect.top - tooltip.offsetHeight - 5}px`;
                tooltip.style.left = `${rect.left + (rect.width - tooltip.offsetWidth) / 2}px`;
            });

            element.addEventListener('mouseleave', () => {
                const tooltip = document.querySelector('.tooltip');
                if (tooltip) tooltip.remove();
            });
        });
    }

    // Initialize tooltips
    initializeTooltips();
});