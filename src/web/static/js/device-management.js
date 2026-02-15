/**
 * Enhanced Device Management JavaScript
 * Provides improved connection management, diagnostics, and user guidance
 */

class DeviceManager {
    constructor() {
        this.connectionStartTime = null;
        this.dataRateCounter = 0;
        this.lastDataTime = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectTimer = null;
        this.autoReconnectEnabled = true;
        this.connectionQualityTimer = null;
        
        this.initializeElements();
        this.bindEvents();
        this.startConnectionMonitoring();
    }
    
    initializeElements() {
        // Basic elements
        this.discoverBtn = document.getElementById('discover-btn');
        this.discoverSpinner = document.getElementById('discover-spinner');
        this.discoverStatus = document.getElementById('discover-status');
        this.deviceList = document.getElementById('device-list');
        this.disconnectBtn = document.getElementById('disconnect-btn');
        this.reconnectBtn = document.getElementById('reconnect-btn');
        this.diagnosticBtn = document.getElementById('diagnostic-btn');
        
        // Status elements
        this.statusText = document.getElementById('status-text');
        this.deviceName = document.getElementById('device-name');
        this.deviceType = document.getElementById('device-type');
        this.deviceAddress = document.getElementById('device-address');
        
        // Connection quality elements
        this.connectionQuality = document.getElementById('connection-quality');
        this.signalStrength = document.getElementById('signal-strength');
        this.connectionTime = document.getElementById('connection-time');
        this.dataRate = document.getElementById('data-rate');
        this.lastDataTimeElement = document.getElementById('last-data-time');
        
        // Auto-reconnect elements
        this.autoReconnectStatus = document.getElementById('auto-reconnect-status');
        this.reconnectAttemptElement = document.getElementById('reconnect-attempt');
        
        // Wizard elements
        this.startWizardBtn = document.getElementById('start-wizard-btn');
        this.pairingWizard = document.getElementById('pairing-wizard');
        this.wizardSteps = document.querySelectorAll('.wizard-step');
        
        // Troubleshooting elements
        this.toggleTroubleshootingBtn = document.getElementById('toggle-troubleshooting');
        this.troubleshootingGuide = document.getElementById('troubleshooting-guide');
        this.diagnosticResults = document.getElementById('diagnostic-results');
        this.diagnosticOutput = document.getElementById('diagnostic-output');
    }
    
    bindEvents() {
        // Basic device management events
        this.discoverBtn?.addEventListener('click', () => this.discoverDevices());
        this.disconnectBtn?.addEventListener('click', () => this.disconnectDevice());
        this.reconnectBtn?.addEventListener('click', () => this.reconnectDevice());
        this.diagnosticBtn?.addEventListener('click', () => this.runDiagnostics());
        
        // Wizard events
        this.startWizardBtn?.addEventListener('click', () => this.startPairingWizard());
        this.bindWizardEvents();
        
        // Troubleshooting events
        this.toggleTroubleshootingBtn?.addEventListener('click', () => this.toggleTroubleshooting());
        
        // Device type selection in wizard
        document.querySelectorAll('input[name="wizard-device-type"]')?.forEach(radio => {
            radio.addEventListener('change', () => this.updateWizardInstructions());
        });
    }
    
    bindWizardEvents() {
        // Wizard navigation
        document.getElementById('wizard-next-1')?.addEventListener('click', () => this.wizardNext(1));
        document.getElementById('wizard-back-2')?.addEventListener('click', () => this.wizardBack(2));
        document.getElementById('wizard-next-2')?.addEventListener('click', () => this.wizardNext(2));
        document.getElementById('wizard-back-3')?.addEventListener('click', () => this.wizardBack(3));
        document.getElementById('wizard-finish')?.addEventListener('click', () => this.finishWizard());
        
        // Pairing mode checkbox
        document.getElementById('pairing-mode-ready')?.addEventListener('change', (e) => {
            document.getElementById('wizard-next-2').disabled = !e.target.checked;
        });
    }
    
    async discoverDevices() {
        this.setDiscoveryState(true);
        
        try {
            const response = await fetch('/api/discover', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.success) {
                if (data.devices && data.devices.length > 0) {
                    this.showDiscoveryStatus(`Found ${data.devices.length} device(s)`, 'success');
                    this.displayDevices(data.devices);
                } else {
                    this.showDiscoveryStatus('No devices found', 'warning');
                    this.showNoDevicesMessage();
                }
            } else {
                throw new Error(data.error || 'Discovery failed');
            }
        } catch (error) {
            this.showDiscoveryStatus(`Error: ${error.message}`, 'danger');
            console.error('Discovery error:', error);
        } finally {
            this.setDiscoveryState(false);
        }
    }
    
    setDiscoveryState(discovering) {
        if (this.discoverBtn) {
            this.discoverBtn.disabled = discovering;
        }
        if (this.discoverSpinner) {
            this.discoverSpinner.classList.toggle('d-none', !discovering);
        }
        if (discovering) {
            this.showDiscoveryStatus('Scanning for devices...', 'info');
        }
    }
    
    showDiscoveryStatus(message, type) {
        if (this.discoverStatus) {
            this.discoverStatus.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
        }
    }
    
    displayDevices(devices) {
        if (!this.deviceList) return;
        
        let html = '<div class="list-group">';
        
        devices.forEach(device => {
            const deviceName = device.name || 'Unknown Device';
            const signalStrength = this.getSignalStrengthBadge(device.rssi);
            
            html += `
                <div class="list-group-item list-group-item-action">
                    <div class="d-flex w-100 justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h5 class="mb-1">${deviceName}</h5>
                            <p class="mb-1 text-muted">Address: ${device.address}</p>
                            <div class="mb-2">
                                <small class="text-muted">Signal: ${signalStrength}</small>
                            </div>
                        </div>
                        <div class="device-actions">
                            <div class="mb-2">
                                <select class="form-select form-select-sm device-type-select" id="device-type-${device.address}">
                                    <option value="auto">Auto-detect</option>
                                    <option value="indoor_bike">Indoor Bike</option>
                                    <option value="rower">Rower</option>
                                    <option value="cross_trainer">Cross Trainer</option>
                                </select>
                            </div>
                            <button class="btn btn-sm btn-primary connect-btn" 
                                    data-address="${device.address}" 
                                    data-name="${deviceName}">
                                Connect
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        this.deviceList.innerHTML = html;
        
        // Bind connect button events
        document.querySelectorAll('.connect-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const address = e.target.dataset.address;
                const name = e.target.dataset.name;
                this.connectToDevice(address, name);
            });
        });
    }
    
    getSignalStrengthBadge(rssi) {
        if (!rssi) return '<span class="badge bg-secondary">Unknown</span>';
        
        if (rssi > -50) return '<span class="badge bg-success">Excellent</span>';
        if (rssi > -70) return '<span class="badge bg-info">Good</span>';
        if (rssi > -85) return '<span class="badge bg-warning">Fair</span>';
        return '<span class="badge bg-danger">Poor</span>';
    }
    
    showNoDevicesMessage() {
        if (this.deviceList) {
            this.deviceList.innerHTML = `
                <div class="text-center p-4">
                    <i class="fas fa-search fa-3x text-muted mb-3"></i>
                    <p class="text-muted">No devices found. Make sure your Rogue Echo equipment is:</p>
                    <ul class="list-unstyled">
                        <li>• Powered on and in pairing mode</li>
                        <li>• Within 10 feet of your computer</li>
                        <li>• Not connected to another app</li>
                    </ul>
                    <button class="btn btn-outline-primary mt-2" onclick="deviceManager.startPairingWizard()">
                        Use Pairing Wizard
                    </button>
                </div>
            `;
        }
    }
    
    async connectToDevice(address, name) {
        this.showDiscoveryStatus(`Connecting to ${name}...`, 'info');
        
        try {
            const deviceTypeSelect = document.getElementById(`device-type-${address}`);
            const deviceType = deviceTypeSelect ? deviceTypeSelect.value : 'auto';
            
            const response = await fetch('/api/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address, device_type: deviceType })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showDiscoveryStatus(`Connected to ${name}`, 'success');
                this.onDeviceConnected(address, name);
                this.resetReconnectAttempts();
            } else {
                throw new Error(data.error || 'Connection failed');
            }
        } catch (error) {
            this.showDiscoveryStatus(`Connection failed: ${error.message}`, 'danger');
            console.error('Connection error:', error);
        }
    }
    
    onDeviceConnected(address, name) {
        this.connectionStartTime = new Date();
        this.highlightConnectedDevice(address);
        this.updateConnectionStatus('connected', name, address);
        this.showConnectionQuality(true);
        this.startConnectionQualityMonitoring();
    }
    
    async disconnectDevice() {
        try {
            const response = await fetch('/api/disconnect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showDiscoveryStatus('Disconnected successfully', 'success');
                this.onDeviceDisconnected();
            } else {
                throw new Error(data.error || 'Disconnection failed');
            }
        } catch (error) {
            this.showDiscoveryStatus(`Disconnection failed: ${error.message}`, 'danger');
            console.error('Disconnection error:', error);
        }
    }
    
    onDeviceDisconnected() {
        this.connectionStartTime = null;
        this.updateConnectionStatus('disconnected');
        this.showConnectionQuality(false);
        this.stopConnectionQualityMonitoring();
        this.clearDeviceHighlight();
        this.hideAutoReconnectStatus();
    }
    
    async reconnectDevice() {
        if (this.deviceAddress && this.deviceAddress.textContent !== 'None') {
            const address = this.deviceAddress.textContent;
            const name = this.deviceName.textContent;
            await this.connectToDevice(address, name);
        }
    }
    
    updateConnectionStatus(status, name = 'None', address = 'None') {
        if (this.statusText) {
            if (status === 'connected') {
                this.statusText.textContent = 'Connected';
                this.statusText.className = 'badge bg-success';
            } else {
                this.statusText.textContent = 'Disconnected';
                this.statusText.className = 'badge bg-secondary';
            }
        }
        
        if (this.deviceName) this.deviceName.textContent = name;
        if (this.deviceAddress) this.deviceAddress.textContent = address;
        if (this.disconnectBtn) this.disconnectBtn.disabled = status !== 'connected';
        if (this.reconnectBtn) {
            this.reconnectBtn.classList.toggle('d-none', status === 'connected');
        }
    }
    
    showConnectionQuality(show) {
        if (this.connectionQuality) {
            this.connectionQuality.classList.toggle('d-none', !show);
        }
    }
    
    startConnectionQualityMonitoring() {
        this.connectionQualityTimer = setInterval(() => {
            this.updateConnectionQualityMetrics();
        }, 1000);
    }
    
    stopConnectionQualityMonitoring() {
        if (this.connectionQualityTimer) {
            clearInterval(this.connectionQualityTimer);
            this.connectionQualityTimer = null;
        }
    }
    
    updateConnectionQualityMetrics() {
        // Update connection time
        if (this.connectionStartTime && this.connectionTime) {
            const elapsed = Math.floor((new Date() - this.connectionStartTime) / 1000);
            this.connectionTime.textContent = this.formatDuration(elapsed);
        }
        
        // Update last data time
        if (this.lastDataTime && this.lastDataTimeElement) {
            const elapsed = Math.floor((new Date() - this.lastDataTime) / 1000);
            if (elapsed < 60) {
                this.lastDataTimeElement.textContent = `${elapsed}s ago`;
            } else {
                this.lastDataTimeElement.textContent = `${Math.floor(elapsed / 60)}m ago`;
            }
        }
    }
    
    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }
    
    highlightConnectedDevice(address) {
        // Remove highlight from all devices
        document.querySelectorAll('.list-group-item').forEach(item => {
            item.classList.remove('active', 'bg-success', 'text-white');
            const connectBtn = item.querySelector('.connect-btn');
            if (connectBtn) {
                connectBtn.disabled = false;
                connectBtn.textContent = 'Connect';
                connectBtn.className = 'btn btn-sm btn-primary connect-btn';
            }
        });
        
        // Highlight connected device
        document.querySelectorAll('.connect-btn').forEach(button => {
            if (button.dataset.address === address) {
                const item = button.closest('.list-group-item');
                item.classList.add('active', 'bg-success', 'text-white');
                button.disabled = true;
                button.textContent = 'Connected';
                button.className = 'btn btn-sm btn-success connect-btn';
            }
        });
    }
    
    clearDeviceHighlight() {
        document.querySelectorAll('.list-group-item').forEach(item => {
            item.classList.remove('active', 'bg-success', 'text-white');
            const connectBtn = item.querySelector('.connect-btn');
            if (connectBtn) {
                connectBtn.disabled = false;
                connectBtn.textContent = 'Connect';
                connectBtn.className = 'btn btn-sm btn-primary connect-btn';
            }
        });
    }
    
    startConnectionMonitoring() {
        // Monitor connection status every 2 seconds
        setInterval(() => {
            this.updateStatus();
        }, 2000);
    }
    
    async updateStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.device_status === 'connected') {
                if (!this.connectionStartTime) {
                    this.connectionStartTime = new Date();
                }
                
                // Update device info
                const deviceName = data.device_name || 'Unknown Device';
                const deviceAddress = data.connected_device_address || 'None';
                
                this.updateConnectionStatus('connected', deviceName, deviceAddress);
                this.showConnectionQuality(true);
                
                // Update connection quality metrics
                if (data.latest_data) {
                    this.lastDataTime = new Date();
                    this.dataRateCounter++;
                    
                    if (this.dataRate) {
                        // Calculate approximate data rate (simplified)
                        this.dataRate.textContent = '1 Hz'; // FTMS typically sends at 1Hz
                    }
                    
                    // Update signal strength based on data quality
                    if (this.signalStrength) {
                        const quality = this.assessDataQuality(data.latest_data);
                        this.signalStrength.textContent = quality.text;
                        this.signalStrength.className = `badge ${quality.class}`;
                    }
                }
                
                this.resetReconnectAttempts();
            } else {
                if (this.connectionStartTime) {
                    // Connection was lost
                    this.onConnectionLost();
                }
                this.updateConnectionStatus('disconnected');
                this.showConnectionQuality(false);
            }
        } catch (error) {
            console.error('Status update error:', error);
        }
    }
    
    assessDataQuality(data) {
        // Simple data quality assessment
        const hasValidPower = data.instant_power !== undefined && data.instant_power >= 0;
        const hasValidHeartRate = data.heart_rate !== undefined && data.heart_rate > 0;
        const hasMovement = data.instant_cadence > 0 || data.instant_speed > 0;
        
        if (hasValidPower && hasMovement) {
            return { text: 'Excellent', class: 'bg-success' };
        } else if (hasValidPower || hasMovement) {
            return { text: 'Good', class: 'bg-info' };
        } else {
            return { text: 'Poor', class: 'bg-warning' };
        }
    }
    
    onConnectionLost() {
        if (this.autoReconnectEnabled && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.startAutoReconnect();
        }
    }
    
    startAutoReconnect() {
        this.reconnectAttempts++;
        this.showAutoReconnectStatus(true);
        
        // Exponential backoff: 2^attempt seconds
        const delay = Math.pow(2, this.reconnectAttempts) * 1000;
        
        this.reconnectTimer = setTimeout(async () => {
            try {
                await this.reconnectDevice();
            } catch (error) {
                console.error('Auto-reconnect failed:', error);
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.startAutoReconnect();
                } else {
                    this.showAutoReconnectStatus(false);
                    this.showDiscoveryStatus('Auto-reconnect failed. Please reconnect manually.', 'warning');
                }
            }
        }, delay);
    }
    
    showAutoReconnectStatus(show) {
        if (this.autoReconnectStatus) {
            this.autoReconnectStatus.classList.toggle('d-none', !show);
        }
        if (show && this.reconnectAttemptElement) {
            this.reconnectAttemptElement.textContent = this.reconnectAttempts;
        }
    }
    
    hideAutoReconnectStatus() {
        this.showAutoReconnectStatus(false);
    }
    
    resetReconnectAttempts() {
        this.reconnectAttempts = 0;
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        this.hideAutoReconnectStatus();
    }
    
    // Pairing Wizard Methods
    startPairingWizard() {
        if (this.pairingWizard) {
            this.pairingWizard.classList.remove('d-none');
            this.showWizardStep(1);
        }
    }
    
    showWizardStep(step) {
        this.wizardSteps.forEach((stepElement, index) => {
            stepElement.classList.toggle('d-none', index + 1 !== step);
        });
    }
    
    updateWizardInstructions() {
        const selectedType = document.querySelector('input[name="wizard-device-type"]:checked')?.value;
        const instructionsElement = document.getElementById('device-instructions');
        const nextButton = document.getElementById('wizard-next-1');
        
        if (selectedType && instructionsElement) {
            let instructions = '';
            
            if (selectedType === 'bike') {
                instructions = `
                    <strong>Rogue Echo Bike Setup:</strong><br>
                    1. Make sure the bike is plugged in and powered on<br>
                    2. Start pedaling to wake up the console<br>
                    3. The display should show the main workout screen
                `;
            } else if (selectedType === 'rower') {
                instructions = `
                    <strong>Rogue Echo Rower Setup:</strong><br>
                    1. Make sure the rower is plugged in and powered on<br>
                    2. Pull the handle to wake up the console<br>
                    3. The display should show the main workout screen
                `;
            }
            
            instructionsElement.innerHTML = instructions;
            instructionsElement.classList.remove('d-none');
            nextButton.disabled = false;
        }
    }
    
    wizardNext(currentStep) {
        if (currentStep === 1) {
            this.setupWizardStep2();
            this.showWizardStep(2);
        } else if (currentStep === 2) {
            this.setupWizardStep3();
            this.showWizardStep(3);
        }
    }
    
    wizardBack(currentStep) {
        this.showWizardStep(currentStep - 1);
    }
    
    setupWizardStep2() {
        const selectedType = document.querySelector('input[name="wizard-device-type"]:checked')?.value;
        const instructionsElement = document.getElementById('pairing-instructions');
        
        let instructions = '';
        if (selectedType === 'bike') {
            instructions = `
                <div class="alert alert-info">
                    <strong>Put your Echo Bike in pairing mode:</strong><br>
                    1. Press and hold the "Connect" button for 2 seconds<br>
                    2. You should hear two beeps<br>
                    3. The Bluetooth and ANT+ icons should start flashing<br>
                    4. The console will display "Ready to Connect"
                </div>
            `;
        } else if (selectedType === 'rower') {
            instructions = `
                <div class="alert alert-info">
                    <strong>Put your Echo Rower in pairing mode:</strong><br>
                    1. From the home screen, select "Connect"<br>
                    2. Choose "Connect to App"<br>
                    3. The Bluetooth icon should start flashing<br>
                    4. The console will display "Ready to Pair"
                </div>
            `;
        }
        
        if (instructionsElement) {
            instructionsElement.innerHTML = instructions;
        }
    }
    
    async setupWizardStep3() {
        const wizardDeviceList = document.getElementById('wizard-device-list');
        if (wizardDeviceList) {
            wizardDeviceList.innerHTML = '<p>Scanning for devices...</p>';
        }
        
        try {
            await this.discoverDevices();
            // The device list will be updated by the discover method
            if (wizardDeviceList) {
                wizardDeviceList.innerHTML = '<p>Select your device from the list above and click Connect.</p>';
            }
        } catch (error) {
            if (wizardDeviceList) {
                wizardDeviceList.innerHTML = `<div class="alert alert-danger">Error scanning: ${error.message}</div>`;
            }
        }
    }
    
    finishWizard() {
        if (this.pairingWizard) {
            this.pairingWizard.classList.add('d-none');
        }
        this.showDiscoveryStatus('Pairing wizard completed successfully!', 'success');
    }
    
    // Diagnostics Methods
    async runDiagnostics() {
        if (this.diagnosticResults) {
            this.diagnosticResults.classList.remove('d-none');
        }
        
        if (this.diagnosticOutput) {
            this.diagnosticOutput.innerHTML = '<p>Running diagnostics...</p>';
        }
        
        const diagnostics = await this.performDiagnostics();
        
        if (this.diagnosticOutput) {
            this.diagnosticOutput.innerHTML = this.formatDiagnosticResults(diagnostics);
        }
    }
    
    async performDiagnostics() {
        const results = {
            timestamp: new Date().toISOString(),
            bluetooth: await this.checkBluetoothStatus(),
            connection: await this.checkConnectionStatus(),
            dataFlow: await this.checkDataFlow(),
            system: await this.checkSystemInfo()
        };

        return results;
    }
    
    async checkBluetoothStatus() {
        // Query the server backend for Bluetooth adapter health
        // (BLE runs on the server, not in the browser)
        try {
            const response = await fetch('/health/detailed');
            const health = await response.json();
            const bt = health.components && health.components.bluetooth;

            if (bt) {
                return {
                    status: bt.status,
                    mode: bt.mode || null,
                    adapters: bt.adapters || [],
                    adapterCount: bt.adapter_count || 0,
                    note: bt.note || null,
                    error: bt.error || null
                };
            }
            return { status: 'unknown', error: 'No Bluetooth info from server' };
        } catch (error) {
            return { status: 'error', error: error.message };
        }
    }
    
    async checkConnectionStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            return {
                deviceStatus: data.device_status,
                connectedDevice: data.connected_device,
                isSimulated: data.is_simulated,
                workoutActive: data.workout_active,
                hasLatestData: !!data.latest_data
            };
        } catch (error) {
            return {
                error: error.message,
                status: 'Error checking connection'
            };
        }
    }
    
    async checkDataFlow() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.latest_data) {
                return {
                    hasData: true,
                    dataAge: 'Recent',
                    powerData: data.latest_data.instant_power !== undefined,
                    heartRateData: data.latest_data.heart_rate !== undefined,
                    cadenceData: data.latest_data.instant_cadence !== undefined
                };
            } else {
                return {
                    hasData: false,
                    status: 'No recent data'
                };
            }
        } catch (error) {
            return {
                error: error.message,
                status: 'Error checking data flow'
            };
        }
    }
    
    async checkSystemInfo() {
        const info = {
            browserPlatform: navigator.platform,
            onLine: navigator.onLine,
            cookieEnabled: navigator.cookieEnabled
        };

        // Fetch server-side system info
        try {
            const response = await fetch('/health/detailed');
            const health = await response.json();
            info.serverStatus = health.status;
            if (health.components && health.components.memory) {
                info.serverMemory = health.components.memory;
            }
        } catch (e) {
            info.serverStatus = 'unreachable';
        }

        return info;
    }
    
    formatDiagnosticResults(diagnostics) {
        let html = `<h6>Diagnostic Results - ${new Date(diagnostics.timestamp).toLocaleString()}</h6>`;
        
        // Bluetooth Status (server adapter)
        html += '<div class="mb-3">';
        html += '<strong>Bluetooth Adapter:</strong><br>';
        if (diagnostics.bluetooth.error) {
            html += `Adapter Status: ❌ ${diagnostics.bluetooth.error}<br>`;
        } else if (diagnostics.bluetooth.mode === 'simulator') {
            html += 'Adapter Status: ✅ Simulator Mode<br>';
        } else if (diagnostics.bluetooth.status === 'healthy') {
            html += `Adapter Status: ✅ Healthy<br>`;
            html += `Adapters Found: ${diagnostics.bluetooth.adapterCount}<br>`;
        } else {
            html += `Adapter Status: ❌ ${diagnostics.bluetooth.status}<br>`;
        }
        html += '</div>';
        
        // Connection Status
        html += '<div class="mb-3">';
        html += '<strong>Connection Status:</strong><br>';
        if (diagnostics.connection.error) {
            html += `❌ Error: ${diagnostics.connection.error}<br>`;
        } else {
            html += `Device Status: ${diagnostics.connection.deviceStatus === 'connected' ? '✅ Connected' : '❌ Disconnected'}<br>`;
            html += `Simulated: ${diagnostics.connection.isSimulated ? 'Yes' : 'No'}<br>`;
            html += `Workout Active: ${diagnostics.connection.workoutActive ? 'Yes' : 'No'}<br>`;
            html += `Recent Data: ${diagnostics.connection.hasLatestData ? '✅' : '❌'}<br>`;
        }
        html += '</div>';
        
        // Data Flow
        html += '<div class="mb-3">';
        html += '<strong>Data Flow:</strong><br>';
        if (diagnostics.dataFlow.error) {
            html += `❌ Error: ${diagnostics.dataFlow.error}<br>`;
        } else if (diagnostics.dataFlow.hasData) {
            html += `Power Data: ${diagnostics.dataFlow.powerData ? '✅' : '❌'}<br>`;
            html += `Heart Rate: ${diagnostics.dataFlow.heartRateData ? '✅' : '❌'}<br>`;
            html += `Cadence: ${diagnostics.dataFlow.cadenceData ? '✅' : '❌'}<br>`;
        } else {
            html += '❌ No data available<br>';
        }
        html += '</div>';
        
        // System Info
        html += '<div class="mb-3">';
        html += '<strong>System Information:</strong><br>';
        html += `Server Status: ${diagnostics.system.serverStatus === 'healthy' ? '✅ Healthy' : '❌ ' + (diagnostics.system.serverStatus || 'Unknown')}<br>`;
        if (diagnostics.system.serverMemory && diagnostics.system.serverMemory.system) {
            const mem = diagnostics.system.serverMemory.system;
            html += `Server Memory: ${mem.available_gb} GB free of ${mem.total_gb} GB (${mem.used_percent}% used)<br>`;
        }
        html += `Network: ${diagnostics.system.onLine ? '✅ Connected' : '❌ Offline'}<br>`;
        html += `Browser: ${diagnostics.system.browserPlatform}<br>`;
        html += '</div>';
        
        return html;
    }
    
    toggleTroubleshooting() {
        if (this.troubleshootingGuide) {
            const isHidden = this.troubleshootingGuide.classList.contains('d-none');
            this.troubleshootingGuide.classList.toggle('d-none');
            
            if (this.toggleTroubleshootingBtn) {
                this.toggleTroubleshootingBtn.textContent = isHidden ? 'Hide Details' : 'Show Details';
            }
        }
    }
}

// Initialize device manager when DOM is loaded
let deviceManager;
document.addEventListener('DOMContentLoaded', function() {
    deviceManager = new DeviceManager();
});