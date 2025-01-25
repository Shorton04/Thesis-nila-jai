// static/js/document-detail.js

document.addEventListener('DOMContentLoaded', function() {
    const updateDocumentBtn = document.getElementById('updateDocumentBtn');
    const uploadModal = document.getElementById('uploadModal');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const updateVersionForm = document.getElementById('updateVersionForm');
    const documentPreview = document.getElementById('documentPreview');

    // Modal handlers
    function showModal() {
        uploadModal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    function hideModal() {
        uploadModal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
    }

    updateDocumentBtn.addEventListener('click', showModal);
    closeModalBtn.addEventListener('click', hideModal);

    // Close modal on outside click
    uploadModal.addEventListener('click', (e) => {
        if (e.target === uploadModal) {
            hideModal();
        }
    });

    // Handle ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !uploadModal.classList.contains('hidden')) {
            hideModal();
        }
    });

    // Version update form handler
    updateVersionForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const formData = new FormData(this);
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.innerHTML;

        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `
                <svg class="animate-spin h-5 w-5 mr-2 inline" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                Uploading...
            `;

            const response = await fetch(updateVersionForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            });

            const result = await response.json();

            if (result.success) {
                showNotification('Version updated successfully', 'success');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                throw new Error(result.error || 'Update failed');
            }
        } catch (error) {
            showNotification(error.message, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
        }
    });

    // Document preview enhancements
    function initializeDocumentPreview() {
        const img = documentPreview.querySelector('img');
        if (!img) return;

        // Add zoom functionality
        let scale = 1;
        let panning = false;
        let pointX = 0;
        let pointY = 0;
        let start = { x: 0, y: 0 };

        function setTransform() {
            img.style.transform = `translate(${pointX}px, ${pointY}px) scale(${scale})`;
        }

        documentPreview.addEventListener('mousedown', (e) => {
            e.preventDefault();
            start = { x: e.clientX - pointX, y: e.clientY - pointY };
            panning = true;
        });

        documentPreview.addEventListener('mousemove', (e) => {
            e.preventDefault();
            if (!panning) return;

            pointX = e.clientX - start.x;
            pointY = e.clientY - start.y;
            setTransform();
        });

        documentPreview.addEventListener('mouseup', () => {
            panning = false;
        });

        documentPreview.addEventListener('wheel', (e) => {
            e.preventDefault();
            const xs = (e.clientX - pointX) / scale;
            const ys = (e.clientY - pointY) / scale;
            const delta = -e.deltaY;

            scale = Math.min(Math.max(1, scale + delta * 0.01), 4);

            pointX = e.clientX - xs * scale;
            pointY = e.clientY - ys * scale;

            setTransform();
        });

        // Add reset button
        const resetBtn = document.createElement('button');
        resetBtn.className = 'absolute top-2 right-2 bg-white rounded-full p-2 shadow-md hover:bg-gray-100';
        resetBtn.innerHTML = `
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
        `;
        resetBtn.addEventListener('click', () => {
            scale = 1;
            pointX = 0;
            pointY = 0;
            setTransform();
        });

        documentPreview.style.position = 'relative';
        documentPreview.appendChild(resetBtn);
    }

    // Initialize preview functionality
    initializeDocumentPreview();

    // Notification system (reused from document-upload.js)
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

        // Animate notification
        requestAnimationFrame(() => {
            notification.classList.add('translate-y-2', 'opacity-100');
        });

        // Remove notification after delay
        setTimeout(() => {
            notification.classList.remove('translate-y-2', 'opacity-100');
            notification.classList.add('-translate-y-2', 'opacity-0');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // Document analysis visualization
    function initializeAnalysisVisualizations() {
        // Confidence score gauge
        function createConfidenceGauge(score, elementId) {
            const gauge = document.getElementById(elementId);
            if (!gauge) return;

            const percentage = Math.min(Math.max(score * 100, 0), 100);
            const color = percentage > 80 ? '#10B981' : percentage > 60 ? '#F59E0B' : '#EF4444';

            gauge.innerHTML = `
                <svg class="w-24 h-24" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r="54" fill="none" stroke="#E5E7EB" stroke-width="12"/>
                    <circle cx="60" cy="60" r="54" fill="none" stroke="${color}" stroke-width="12"
                            stroke-dasharray="${percentage * 3.39}, 339.292"
                            transform="rotate(-90 60 60)"/>
                    <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" 
                          class="text-xl font-bold" fill="${color}">
                        ${percentage.toFixed(0)}%
                    </text>
                </svg>
            `;
        }

        // Fraud detection visualization
        function createFraudDetectionChart(data, elementId) {
            const container = document.getElementById(elementId);
            if (!container) return;

            const categories = Object.keys(data);
            const maxScore = Math.max(...Object.values(data));

            container.innerHTML = categories.map(category => `
                <div class="mb-4">
                    <div class="flex justify-between items-center mb-1">
                        <span class="text-sm font-medium text-gray-600">${category}</span>
                        <span class="text-sm text-gray-500">${(data[category] * 100).toFixed(1)}%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div class="bg-blue-600 h-2 rounded-full" 
                             style="width: ${(data[category] / maxScore * 100)}%"></div>
                    </div>
                </div>
            `).join('');
        }

        // Version history timeline
        function createVersionTimeline() {
            const versions = Array.from(document.querySelectorAll('[data-version]'));
            if (versions.length === 0) return;

            const timeline = document.createElement('div');
            timeline.className = 'relative mt-8 before:absolute before:inset-0 before:h-full before:w-0.5 before:bg-gray-200 before:left-4';

            versions.forEach((version, index) => {
                const versionData = JSON.parse(version.dataset.version);
                const timelineItem = document.createElement('div');
                timelineItem.className = 'relative flex items-start mb-8 ml-8';

                timelineItem.innerHTML = `
                    <div class="absolute -left-10 mt-1.5">
                        <span class="flex items-center justify-center w-6 h-6 rounded-full border-2 
                                   ${index === 0 ? 'bg-blue-500 border-blue-500' : 'bg-white border-gray-300'}">
                            <svg class="w-3 h-3 ${index === 0 ? 'text-white' : 'text-gray-500'}" 
                                 fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" 
                                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" 
                                      clip-rule="evenodd"/>
                            </svg>
                        </span>
                    </div>
                    <div class="flex-grow">
                        <div class="mb-1">
                            <span class="text-sm font-medium text-gray-900">Version ${versionData.number}</span>
                            <span class="text-sm text-gray-500 ml-2">${versionData.date}</span>
                        </div>
                        ${versionData.changes ? `
                            <div class="text-sm text-gray-600">${versionData.changes}</div>
                        ` : ''}
                    </div>
                `;

                timeline.appendChild(timelineItem);
            });

            const container = document.getElementById('versionTimeline');
            if (container) {
                container.appendChild(timeline);
            }
        }

        // Document preview enhancements
        function enhanceDocumentPreview() {
            const preview = document.getElementById('documentPreview');
            if (!preview) return;

            // Add toolbar
            const toolbar = document.createElement('div');
            toolbar.className = 'absolute top-0 left-0 right-0 bg-gray-800 bg-opacity-75 text-white p-2 flex justify-end space-x-2';
            toolbar.innerHTML = `
                <button class="p-1 hover:bg-gray-700 rounded" id="zoomIn" title="Zoom In">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                    </svg>
                </button>
                <button class="p-1 hover:bg-gray-700 rounded" id="zoomOut" title="Zoom Out">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/>
                    </svg>
                </button>
                <button class="p-1 hover:bg-gray-700 rounded" id="rotateRight" title="Rotate Right">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                </button>
            `;

            preview.style.position = 'relative';
            preview.insertBefore(toolbar, preview.firstChild);

            // Initialize preview controls
            let scale = 1;
            let rotation = 0;
            const image = preview.querySelector('img');

            document.getElementById('zoomIn').addEventListener('click', () => {
                scale = Math.min(scale + 0.2, 3);
                updateTransform();
            });

            document.getElementById('zoomOut').addEventListener('click', () => {
                scale = Math.max(scale - 0.2, 0.5);
                updateTransform();
            });

            document.getElementById('rotateRight').addEventListener('click', () => {
                rotation = (rotation + 90) % 360;
                updateTransform();
            });

            function updateTransform() {
                image.style.transform = `rotate(${rotation}deg) scale(${scale})`;
            }
        }

        // Initialize all visualizations
        const documentData = window.documentAnalysis || {};
        if (documentData.confidenceScore) {
            createConfidenceGauge(documentData.confidenceScore, 'confidenceGauge');
        }
        if (documentData.fraudDetection) {
            createFraudDetectionChart(documentData.fraudDetection, 'fraudDetectionChart');
        }
        createVersionTimeline();
        enhanceDocumentPreview();
    }

    // Initialize analysis visualizations
    initializeAnalysisVisualizations();
});