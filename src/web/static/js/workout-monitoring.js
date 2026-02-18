/**
 * Real-time Workout Monitoring with Enhanced Features
 * Implements optimized data polling, client-side caching, responsive charts,
 * and workout phase indicators for improved user experience.
 */

class WorkoutMonitor {
    constructor() {
        this.isActive = false;
        this.pollInterval = null;
        this.pollRate = 1000; // 1 second default
        this.adaptivePollRate = true;
        
        // Data caching
        this.dataCache = {
            status: null,
            lastUpdate: 0,
            workoutData: [],
            maxCacheSize: 300 // 5 minutes at 1Hz
        };
        
        // Chart management
        this.charts = {};
        this.chartUpdateQueue = [];
        this.isUpdatingCharts = false;
        
        // Workout phase tracking
        this.workoutPhases = {
            current: 'inactive',
            startTime: null,
            phases: []
        };
        
        // Performance monitoring
        this.performance = {
            updateTimes: [],
            droppedUpdates: 0,
            lastUpdateTime: 0
        };
        
        // Connection quality monitoring
        this.connectionQuality = {
            consecutiveFailures: 0,
            lastSuccessTime: Date.now(),
            quality: 'good' // good, fair, poor, disconnected
        };

        // Unit system preference
        this.userUnitSystem = 'metric';
        this.unitConversions = {
            kphToMph: (kph) => kph * 0.621371,
            mToMi: (m) => m / 1609.34
        };

        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.initializeCharts();
        this.loadUserPreferences();
        console.log('WorkoutMonitor initialized');
    }
    
    setupEventListeners() {
        // Window visibility change for adaptive polling
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.reducePollRate();
            } else {
                this.restorePollRate();
            }
        });
        
        // Network status monitoring
        window.addEventListener('online', () => {
            console.log('Network connection restored');
            this.connectionQuality.quality = 'good';
            this.updateConnectionIndicator();
        });
        
        window.addEventListener('offline', () => {
            console.log('Network connection lost');
            this.connectionQuality.quality = 'disconnected';
            this.updateConnectionIndicator();
        });
        
        // Resize handler for responsive charts
        window.addEventListener('resize', this.debounce(() => {
            this.resizeCharts();
        }, 250));

        // Event Listeners for Workout Buttons
        const startWorkoutBtn = document.getElementById('start-workout-btn');
        const endWorkoutBtn = document.getElementById('end-workout-btn');

        if (startWorkoutBtn) {
            startWorkoutBtn.addEventListener("click", async () => {
                try {
                    // Debug: Log the current status cache
                    console.log("Current status cache:", this.dataCache.status);
                    
                    const connectedDeviceAddress = this.dataCache.status?.connected_device_address;
                    const connectedDeviceName = this.dataCache.status?.connected_device?.name;
                    
                    console.log("Connected device address:", connectedDeviceAddress);
                    console.log("Connected device name:", connectedDeviceName);
                    console.log("Device status:", this.dataCache.status?.device_status);

                    if (!connectedDeviceAddress || !connectedDeviceName) {
                        console.error("Cannot start workout: Device address or name is missing.");
                        alert("Cannot start workout: Please ensure a device is connected.");
                        return;
                    }

                    const workoutType = connectedDeviceName.toLowerCase().includes("rower") ? "rower" : "bike";

                    const response = await fetch("/api/start_workout", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                            device_id: connectedDeviceAddress, 
                            workout_type: workoutType,
                        }),
                    });
                    const data = await response.json();
                    if (data.success) {
                        console.log("Workout started successfully:", data.workout_id);
                        this.start(); // Start monitoring
                        // Force status refresh to update button states and UI
                        await this.fetchWorkoutData();
                    } else {
                        console.error("Failed to start workout:", data.error);
                        alert("Failed to start workout: " + data.error);
                    }
                } catch (error) {
                    console.error("Error starting workout:", error);
                    alert("Error starting workout: " + error.message);
                }
            });
        }

        if (endWorkoutBtn) {
            endWorkoutBtn.addEventListener("click", async () => {
                try {
                    const response = await fetch("/api/end_workout", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                    });
                    const data = await response.json();
                    if (data.success) {
                        console.log("Workout ended successfully.");
                        this.stop(); // Stop monitoring
                    } else {
                        console.error("Failed to end workout:", data.error);
                        alert("Failed to end workout: " + data.error);
                    }
                } catch (error) {
                    console.error("Error ending workout:", error);
                    alert("Error ending workout: " + error.message);
                }
            });
        }
    }
    
    async loadUserPreferences() {
        try {
            const response = await fetch('/api/settings');
            const data = await response.json();

            if (data.success && data.settings) {
                this.pollRate = data.settings.poll_rate || 1000;
                this.adaptivePollRate = data.settings.adaptive_polling !== false;

                // Load unit system preference
                if (data.settings.unit_system) {
                    this.userUnitSystem = data.settings.unit_system;
                }

                // Update chart preferences
                if (data.settings.chart_preferences) {
                    this.updateChartPreferences(data.settings.chart_preferences);
                }
            }

            // Also check user profile for unit preference
            if (this.userUnitSystem === 'metric') {
                try {
                    const profileResponse = await fetch('/api/user_profile');
                    const profileData = await profileResponse.json();
                    if (profileData && profileData.success && profileData.profile && profileData.profile.unit_preference) {
                        this.userUnitSystem = profileData.profile.unit_preference;
                    }
                } catch (e) {
                    // Ignore profile fetch errors
                }
            }
        } catch (error) {
            console.warn('Could not load user preferences:', error);
        }
    }

    start() {
        if (this.isActive) return;
        
        this.isActive = true;
        this.workoutPhases.startTime = Date.now();
        this.workoutPhases.current = 'warmup';
        
        console.log('Starting workout monitoring');
        this.startPolling();
        this.updateWorkoutPhaseIndicator();
    }
    
    stop() {
        if (!this.isActive) return;
        
        this.isActive = false;
        this.workoutPhases.current = 'inactive';
        
        console.log('Stopping workout monitoring');
        this.stopPolling();
        this.updateWorkoutPhaseIndicator();
    }
    
    startPolling() {
        this.stopPolling(); // Clear any existing interval
        
        this.pollInterval = setInterval(() => {
            this.fetchWorkoutData();
        }, this.pollRate);
        
        // Initial fetch
        this.fetchWorkoutData();
    }
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
    
    handleFetchError(error) {
        // Handle fetch errors and update connection quality
        this.connectionQuality.consecutiveFailures++;
        
        if (this.connectionQuality.consecutiveFailures >= 3) {
            this.updateConnectionQuality('poor');
        } else if (this.connectionQuality.consecutiveFailures >= 2) {
            this.updateConnectionQuality('fair');
        }
        
        // If too many consecutive failures, reduce poll rate
        if (this.connectionQuality.consecutiveFailures >= 5 && this.pollRate < 5000) {
            this.pollRate = Math.min(this.pollRate * 2, 5000);
            this.stopPolling();
            this.startPolling();
            console.warn(`Increased poll rate to ${this.pollRate}ms due to connection issues`);
        }
        
        // Log the error for debugging
        console.error('Fetch error details:', {
            error: error.message,
            consecutiveFailures: this.connectionQuality.consecutiveFailures,
            pollRate: this.pollRate
        });
    }
    
    cacheData(data) {
        const now = Date.now();
        
        // Update status cache
        this.dataCache.status = data;
        this.dataCache.lastUpdate = now;
        
        // Cache workout data points
        if (data.latest_data && this.isActive) {
            this.dataCache.workoutData.push({
                timestamp: now,
                data: { ...data.latest_data }
            });
            
            // Maintain cache size
            if (this.dataCache.workoutData.length > this.dataCache.maxCacheSize) {
                this.dataCache.workoutData.shift();
            }
        }
    }
    
    processWorkoutData(data) {
        if (!data) return;
        
        // Update UI elements
        this.updateStatusDisplay(data);
        this.updateMetricsDisplay(data);
        
        // Update charts if workout is active
        if (this.isActive && data.latest_data) {
            this.queueChartUpdate(data.latest_data);
        }
        
        // Update workout phase
        this.updateWorkoutPhase(data);
        
        // Update workout summary
        if (data.latest_data && data.latest_data.workout_summary) {
            this.updateWorkoutSummary(data.latest_data.workout_summary);
        }

        // Update button states based on connection and workout status
        this.updateButtonStates(data.device_status, data.workout_active);

        // If workout is active but end button is disabled, force UI update
        const endWorkoutBtn = document.getElementById("end-workout-btn");
        if (data.workout_active && endWorkoutBtn && endWorkoutBtn.disabled) {
            endWorkoutBtn.disabled = false;
        }
        // If workout is active and summary is missing, force summary update
        if (data.workout_active && (!data.latest_data || !data.latest_data.workout_summary)) {
            this.updateWorkoutSummary({});
        }
    }
    
    updateStatusDisplay(data) {
        const elements = {
            statusText: document.getElementById('status-text'),
            deviceName: document.getElementById('device-name'),
            workoutStatus: document.getElementById('workout-status'),
            workoutDuration: document.getElementById('workout-duration')
        };
        
        // Update connection status
        if (elements.statusText) {
            if (data.device_status === 'connected') {
                elements.statusText.textContent = 'Connected';
                elements.statusText.className = 'badge bg-success';
            } else {
                elements.statusText.textContent = 'Disconnected';
                elements.statusText.className = 'badge bg-secondary';
            }
        }
        
        // Update device name
        if (elements.deviceName) {
            const deviceName = data.device_name || 
                             (data.connected_device && data.connected_device.name) || 
                             'None';
            elements.deviceName.textContent = deviceName;
        }
        
        // Update workout status
        if (elements.workoutStatus) {
            if (data.workout_active) {
                elements.workoutStatus.textContent = 'Active';
                elements.workoutStatus.className = 'badge bg-success';
            } else {
                elements.workoutStatus.textContent = 'Inactive';
                elements.workoutStatus.className = 'badge bg-secondary';
            }
        }
        
        // Update workout duration
        if (elements.workoutDuration && data.latest_data && data.latest_data.elapsed_time) {
            elements.workoutDuration.textContent = this.formatDuration(data.latest_data.elapsed_time);
        }
    }
    
    updateMetricsDisplay(data) {
        if (!data.latest_data) return;
        
        const metrics = data.latest_data;
        const elements = {
            power: document.getElementById('power-value'),
            heartRate: document.getElementById('heart-rate-value'),
            cadence: document.getElementById('cadence-value'),
            speed: document.getElementById('speed-value'),
            distance: document.getElementById('distance-value'),
            calories: document.getElementById('calories-value')
        };
        
        // Update power
        if (elements.power && (metrics.instant_power !== undefined || metrics.power !== undefined)) {
            const power = metrics.instant_power || metrics.power || 0;
            elements.power.textContent = Math.round(power);
            this.addMetricAnimation(elements.power, power);
        }
        
        // Update heart rate
        if (elements.heartRate && metrics.heart_rate !== undefined) {
            const heartRate = Math.round(metrics.heart_rate);
            elements.heartRate.textContent = heartRate;
            this.addMetricAnimation(elements.heartRate, metrics.heart_rate);
            
            // Add visual indicator for potential heart rate issues
            const heartRateContainer = elements.heartRate.parentElement;
            if (heartRate > 0 && heartRate < 80) {
                // Add warning indicator for low heart rate
                if (!heartRateContainer.querySelector('.hr-warning')) {
                    const warning = document.createElement('span');
                    warning.className = 'hr-warning';
                    warning.innerHTML = ' ⚠️';
                    warning.title = 'Heart rate seems low - check sensor connection';
                    warning.style.color = '#ffc107';
                    heartRateContainer.appendChild(warning);
                }
            } else {
                // Remove warning if heart rate is normal
                const warning = heartRateContainer.querySelector('.hr-warning');
                if (warning) {
                    warning.remove();
                }
            }
        }
        
        // Update cadence/stroke rate
        if (elements.cadence) {
            const workoutType = metrics.type || metrics.device_type || 'bike';
            let cadenceValue = 0;
            
            if (workoutType === 'bike') {
                cadenceValue = metrics.instant_cadence || metrics.instantaneous_cadence || metrics.cadence || 0;
            } else if (workoutType === 'rower') {
                cadenceValue = metrics.stroke_rate || 0;
            }
            
            elements.cadence.textContent = Math.round(cadenceValue);
            this.addMetricAnimation(elements.cadence, cadenceValue);
        }
        
        // Update speed with unit conversion
        if (elements.speed && (metrics.instant_speed !== undefined || metrics.speed !== undefined)) {
            let speed = metrics.instant_speed || metrics.speed || 0;
            const speedUnitEl = document.querySelector('.metric-card:has(#speed-value) .metric-unit');
            if (this.userUnitSystem === 'imperial') {
                speed = this.unitConversions.kphToMph(speed);
                if (speedUnitEl) speedUnitEl.textContent = 'mph';
            } else {
                if (speedUnitEl) speedUnitEl.textContent = 'km/h';
            }
            elements.speed.textContent = speed.toFixed(1);
            this.addMetricAnimation(elements.speed, speed);
        }

        // Update distance with unit conversion
        if (elements.distance && (metrics.total_distance !== undefined || metrics.distance !== undefined)) {
            const distanceM = metrics.total_distance || metrics.distance || 0;
            const distanceUnitEl = document.querySelector('.metric-card:has(#distance-value) .metric-unit');
            if (this.userUnitSystem === 'imperial') {
                const distanceMi = this.unitConversions.mToMi(distanceM);
                elements.distance.textContent = distanceMi.toFixed(2);
                if (distanceUnitEl) distanceUnitEl.textContent = 'mi';
            } else {
                const distanceKm = distanceM / 1000;
                elements.distance.textContent = distanceKm.toFixed(2);
                if (distanceUnitEl) distanceUnitEl.textContent = 'km';
            }
        }
        
        // Update calories
        if (elements.calories && (metrics.total_energy !== undefined || metrics.calories !== undefined)) {
            const calories = metrics.total_energy || metrics.calories || 0;
            elements.calories.textContent = Math.round(calories);
        }
    }
    
    addMetricAnimation(element, value) {
        // Add subtle animation for metric changes
        element.style.transform = 'scale(1.05)';
        element.style.transition = 'transform 0.1s ease-out';
        
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 100);
        
        // Add color coding for power zones
        if (element.id === 'power-value') {
            this.updatePowerZoneColor(element, value);
        }
    }
    
    updatePowerZoneColor(element, power) {
        // Remove existing zone classes
        element.classList.remove('power-zone-1', 'power-zone-2', 'power-zone-3', 'power-zone-4', 'power-zone-5');
        
        // Add appropriate zone class based on power
        if (power > 250) {
            element.classList.add('power-zone-5'); // Neuromuscular Power
        } else if (power > 200) {
            element.classList.add('power-zone-4'); // Lactate Threshold
        } else if (power > 150) {
            element.classList.add('power-zone-3'); // Tempo
        } else if (power > 100) {
            element.classList.add('power-zone-2'); // Endurance
        } else if (power > 50) {
            element.classList.add('power-zone-1'); // Active Recovery
        }
    }
    
    queueChartUpdate(data) {
        this.chartUpdateQueue.push(data);
        
        if (!this.isUpdatingCharts) {
            this.processChartUpdateQueue();
        }
    }
    
    async updateCharts(data) {
        const maxDataPoints = 60; // 1 minute of data
        
        // Update power chart
        if (this.charts.power && (data.instant_power !== undefined || data.power !== undefined)) {
            const power = data.instant_power || data.power || 0;
            this.updateChartData(this.charts.power, power, maxDataPoints);
        }
        
        // Update heart rate chart
        if (this.charts.heartRate && data.heart_rate !== undefined) {
            this.updateChartData(this.charts.heartRate, data.heart_rate, maxDataPoints);
        }
        
        // Update cadence chart
        if (this.charts.cadence) {
            const workoutType = data.type || data.device_type || 'bike';
            let cadenceValue = 0;
            
            if (workoutType === 'bike') {
                cadenceValue = data.instant_cadence || data.instantaneous_cadence || data.cadence || 0;
            } else if (workoutType === 'rower') {
                cadenceValue = data.stroke_rate || 0;
            }
            
            this.updateChartData(this.charts.cadence, cadenceValue, maxDataPoints);
        }
        
        // Batch update all charts
        this.batchUpdateCharts();
    }
    
    updateChartData(chart, value, maxDataPoints) {
        if (!chart || !chart.data || !chart.data.datasets[0]) return;
        
        const dataset = chart.data.datasets[0];
        dataset.data.push(value);
        
        // Maintain max data points
        if (dataset.data.length > maxDataPoints) {
            dataset.data.shift();
        }
        
        // Mark chart as needing update
        chart._needsUpdate = true;
    }
    
    batchUpdateCharts() {
        // Use requestAnimationFrame for smooth updates
        requestAnimationFrame(() => {
            Object.values(this.charts).forEach(chart => {
                if (chart._needsUpdate) {
                    chart.update('none'); // No animation for real-time updates
                    chart._needsUpdate = false;
                }
            });
        });
    }
    
    updateWorkoutPhase(data) {
        if (!this.isActive || !data.latest_data) return;
        
        const elapsed = data.latest_data.elapsed_time || 0;
        const power = data.latest_data.instant_power || data.latest_data.power || 0;
        
        let newPhase = this.determineWorkoutPhase(elapsed, power);
        
        if (newPhase !== this.workoutPhases.current) {
            this.workoutPhases.current = newPhase;
            this.workoutPhases.phases.push({
                phase: newPhase,
                startTime: elapsed,
                timestamp: Date.now()
            });
            
            this.updateWorkoutPhaseIndicator();
            this.showPhaseTransitionNotification(newPhase);
        }
    }
    
    determineWorkoutPhase(elapsed, power) {
        // Simple phase detection based on time and power
        if (elapsed < 300) { // First 5 minutes
            return 'warmup';
        } else if (elapsed < 600) { // 5-10 minutes
            return power > 150 ? 'main' : 'warmup';
        } else if (elapsed > 1800) { // After 30 minutes
            return power < 100 ? 'cooldown' : 'main';
        } else {
            return 'main';
        }
    }
    
    updateWorkoutPhaseIndicator() {
        const workoutPhaseIndicator = document.getElementById('workout-phase-indicator');
        if (workoutPhaseIndicator) {
            let phaseText = '';
            let badgeClass = 'bg-secondary';
            switch (this.workoutPhases.current) {
                case 'warmup':
                    phaseText = '🔥 Warmup';
                    badgeClass = 'bg-info';
                    break;
                case 'main':
                    phaseText = '💪 Main';
                    badgeClass = 'bg-success';
                    break;
                case 'cooldown':
                    phaseText = '🧘 Cooldown';
                    badgeClass = 'bg-warning';
                    break;
                case 'inactive':
                default:
                    phaseText = '⏸️ Inactive';
                    badgeClass = 'bg-secondary';
                    break;
            }
            workoutPhaseIndicator.innerHTML = `<span class="badge ${badgeClass}">${phaseText}</span>`;
        }
    }

    showPhaseTransitionNotification(newPhase) {
        // Implement a toast or similar notification for phase transitions
        console.log(`Workout phase transitioned to: ${newPhase}`);
        // Example: You might use a library like Toastify.js or Bootstrap toasts here
    }

    formatDuration(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        return [
            h.toString().padStart(2, '0'),
            m.toString().padStart(2, '0'),
            s.toString().padStart(2, '0')
        ].join(':');
    }

    updateConnectionIndicator() {
        const indicator = document.getElementById('connection-quality-indicator');
        if (indicator) {
            let icon = '';
            let color = '';
            switch (this.connectionQuality.quality) {
                case 'good':
                    icon = '🟢';
                    color = 'text-success';
                    break;
                case 'fair':
                    icon = '🟡';
                    color = 'text-warning';
                    break;
                case 'poor':
                    icon = '🟠';
                    color = 'text-danger';
                    break;
                case 'disconnected':
                    icon = '🔴';
                    color = 'text-danger';
                    break;
            }
            indicator.innerHTML = `<span class="${color}">${icon}</span>`;
        }
    }

    updateConnectionQuality(quality) {
        this.connectionQuality.quality = quality;
        this.updateConnectionIndicator();
    }

    trackPerformance(updateTime) {
        this.performance.updateTimes.push(updateTime);
        if (this.performance.updateTimes.length > 100) {
            this.performance.updateTimes.shift();
        }
        const avgUpdateTime = this.performance.updateTimes.reduce((a, b) => a + b, 0) / this.performance.updateTimes.length;
        // console.log(`Avg UI update time: ${avgUpdateTime.toFixed(2)}ms`);

        // Check for dropped updates (if polling rate is faster than update time)
        const now = performance.now();
        if (this.performance.lastUpdateTime > 0 && (now - this.performance.lastUpdateTime) > (this.pollRate * 1.5)) { // If actual interval is 1.5x expected
            this.performance.droppedUpdates++;
            console.warn(`Dropped UI update. Total dropped: ${this.performance.droppedUpdates}`);
        }
        this.performance.lastUpdateTime = now;
    }

    adjustPollRate(data) {
        // Example: Reduce poll rate if no new data for a while
        const now = Date.now();
        if (data.latest_data && data.latest_data.timestamp) {
            const lastDataTimestamp = new Date(data.latest_data.timestamp).getTime();
            if ((now - lastDataTimestamp) > (this.pollRate * 5) && this.pollRate < 5000) { // If no new data for 5 poll cycles
                this.pollRate += 500; // Increase poll rate by 500ms
                this.stopPolling();
                this.startPolling();
                console.log(`Adjusted poll rate to: ${this.pollRate}ms`);
            }
        } else if (!data.latest_data && this.pollRate < 5000) { // If no data at all, slow down polling
             this.pollRate += 500; // Increase poll rate by 500ms
             this.stopPolling();
             this.startPolling();
             console.log(`Adjusted poll rate to: ${this.pollRate}ms (no data)`);
        }

        // If workout is active and data is flowing, ensure optimal poll rate
        if (data.workout_active && data.latest_data && this.pollRate !== 1000) {
            this.pollRate = 1000; // Reset to default for active workout
            this.stopPolling();
            this.startPolling();
            console.log(`Reset poll rate to: ${this.pollRate}ms (workout active)`);
        }
    }

    reducePollRate() {
        if (this.adaptivePollRate && this.pollRate < 5000) { // Max 5 seconds when hidden
            this.pollRate = 5000;
            this.stopPolling();
            this.startPolling();
            console.log(`Reduced poll rate due to tab hidden: ${this.pollRate}ms`);
        }
    }

    restorePollRate() {
        if (this.adaptivePollRate && this.pollRate !== 1000) {
            this.pollRate = 1000; // Restore to default
            this.stopPolling();
            this.startPolling();
            console.log(`Restored poll rate due to tab visible: ${this.pollRate}ms`);
        }
    }

    debounce(func, delay) {
        let timeout;
        return function(...args) {
            const context = this;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), delay);
        };
    }

    initializeCharts() {
        // Ensure Chart.js is loaded and DOM elements exist
        const powerChartCtx = document.getElementById('power-chart');
        const heartRateChartCtx = document.getElementById('heart-rate-chart');
        const cadenceChartCtx = document.getElementById('cadence-chart');

        if (!powerChartCtx || !heartRateChartCtx || !cadenceChartCtx || typeof Chart === 'undefined') {
            console.warn('Chart elements or Chart.js not found. Charts will not be initialized.');
            return;
        }

        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    display: false
                },
                y: {
                    beginAtZero: true
                }
            },
            animation: {
                duration: 0
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        };

        const createChart = (ctxId, label, borderColor, backgroundColor) => {
            const ctx = document.getElementById(ctxId)?.getContext('2d');
            if (!ctx) return null; // Return null if context is not found

            return new Chart(ctx, {
                type: 'line',
                data: {
                    labels: Array(60).fill(''), // 60 data points for 1 minute
                    datasets: [{
                        label: label,
                        data: Array(60).fill(null),
                        borderColor: borderColor,
                        backgroundColor: backgroundColor,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: chartOptions
            });
        };

        this.charts.power = createChart('power-chart', 'Power (watts)', 'rgba(255, 99, 132, 1)', 'rgba(255, 99, 132, 0.2)');
        this.charts.heartRate = createChart('heart-rate-chart', 'Heart Rate (bpm)', 'rgba(54, 162, 235, 1)', 'rgba(54, 162, 235, 0.2)');
        this.charts.cadence = createChart('cadence-chart', 'Cadence (rpm)', 'rgba(75, 192, 192, 1)', 'rgba(75, 192, 192, 0.2)');
    }

    updateChartPreferences(preferences) {
        // This method can be expanded to apply user-defined chart preferences
        // e.g., changing colors, line styles, visible charts, etc.
        console.log('Applying chart preferences:', preferences);
    }
    
    resizeCharts() {
        // Resize all charts when window is resized
        Object.values(this.charts).forEach(chart => {
            if (chart && chart.resize) {
                chart.resize();
            }
        });
    }
    
    updateWorkoutSummary(summaryData) {
        // Update the workout summary display
        const summaryElement = document.getElementById('workout-summary');
        if (!summaryElement) return;
        
        if (!summaryData || Object.keys(summaryData).length === 0) {
            summaryElement.innerHTML = '<p>Start a workout to see summary metrics.</p>';
            return;
        }
        
        // Create summary HTML
        let html = '<div class="row">';
        
        // Average power
        const avgPower = summaryData.avg_power || 0;
        html += `
            <div class="col-6">
                <p><strong>Avg Power:</strong> <span>${Math.round(avgPower)}</span> W</p>
            </div>
        `;
        
        // Average heart rate
        const avgHeartRate = summaryData.avg_heart_rate || 0;
        html += `
            <div class="col-6">
                <p><strong>Avg Heart Rate:</strong> <span>${Math.round(avgHeartRate)}</span> bpm</p>
            </div>
        `;
        
        // Average cadence or stroke rate
        const workoutType = summaryData.workout_type || 'bike';
        if (workoutType === 'bike') {
            const avgCadence = summaryData.avg_cadence || 0;
            html += `
                <div class="col-6">
                    <p><strong>Avg Cadence:</strong> <span>${Math.round(avgCadence)}</span> rpm</p>
                </div>
            `;
        } else if (workoutType === 'rower') {
            const avgStrokeRate = summaryData.avg_stroke_rate || 0;
            html += `
                <div class="col-6">
                    <p><strong>Avg Stroke Rate:</strong> <span>${Math.round(avgStrokeRate)}</span> spm</p>
                </div>
            `;
        }
        
        // Average speed with unit conversion
        let avgSpeed = summaryData.avg_speed || 0;
        let speedUnitText = 'km/h';
        if (this.userUnitSystem === 'imperial') {
            avgSpeed = this.unitConversions.kphToMph(avgSpeed);
            speedUnitText = 'mph';
        }
        html += `
            <div class="col-6">
                <p><strong>Avg Speed:</strong> <span>${avgSpeed.toFixed(1)}</span> ${speedUnitText}</p>
            </div>
        `;

        // Total distance with unit conversion
        const totalDistance = summaryData.total_distance || 0;
        let distanceDisplay, distanceUnitText;
        if (this.userUnitSystem === 'imperial') {
            distanceDisplay = this.unitConversions.mToMi(totalDistance).toFixed(2);
            distanceUnitText = 'mi';
        } else {
            distanceDisplay = (totalDistance / 1000).toFixed(2);
            distanceUnitText = 'km';
        }
        html += `
            <div class="col-6">
                <p><strong>Total Distance:</strong> <span>${distanceDisplay}</span> ${distanceUnitText}</p>
            </div>
        `;
        
        // Total calories
        const totalCalories = summaryData.total_calories || 0;
        html += `
            <div class="col-6">
                <p><strong>Total Calories:</strong> <span>${Math.round(totalCalories)}</span> kcal</p>
            </div>
        `;

        // Estimated VO2 Max
        const vo2max = summaryData.estimated_vo2max;
        if (vo2max !== undefined && vo2max > 0) {
            html += `
                <div class="col-6">
                    <p><strong>Est. VO2 Max:</strong> <span>${isNaN(vo2max) ? '-' : vo2max.toFixed(1)}</span> ml/kg/min</p>
                </div>
            `;
        } else {
            html += `
                <div class="col-6">
                    <p><strong>Est. VO2 Max:</strong> <span>-</span> <i class="fa fa-info-circle" title="Requires: age &amp; weight in Settings, HR monitor, avg HR above 70% of max HR"></i></p>
                </div>
            `;
        }

        html += '</div>';
        summaryElement.innerHTML = html;
    }
    
    async fetchWorkoutData() {
        const startTime = performance.now();
        
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            // Update connection quality
            this.connectionQuality.consecutiveFailures = 0;
            this.connectionQuality.lastSuccessTime = Date.now();
            this.updateConnectionQuality('good');
            
            // Cache the data
            this.cacheData(data);
            
            // Process the data
            this.processWorkoutData(data);
            
            // Track performance
            const updateTime = performance.now() - startTime;
            this.trackPerformance(updateTime);
            
            // Adaptive polling based on data changes
            if (this.adaptivePollRate) {
                this.adjustPollRate(data);
            }
            
        } catch (error) {
            console.error('Error fetching workout data:', error);
            this.handleFetchError(error);
        }
    }
    
    async processChartUpdateQueue() {
        if (this.chartUpdateQueue.length === 0) return;
        
        this.isUpdatingCharts = true;
        
        // Process all queued updates
        while (this.chartUpdateQueue.length > 0) {
            const data = this.chartUpdateQueue.shift();
            await this.updateCharts(data);
        }
        
        this.isUpdatingCharts = false;
    }
    
    async updateCharts(data) {
        const maxDataPoints = 60; // 1 minute of data
        
        // Update power chart
        if (this.charts.power && (data.instant_power !== undefined || data.power !== undefined)) {
            const power = data.instant_power || data.power || 0;
            this.updateChartData(this.charts.power, power, maxDataPoints);
        }
        
        // Update heart rate chart
        if (this.charts.heartRate && data.heart_rate !== undefined) {
            this.updateChartData(this.charts.heartRate, data.heart_rate, maxDataPoints);
        }
        
        // Update cadence chart
        if (this.charts.cadence) {
            const workoutType = data.type || data.device_type || 'bike';
            let cadenceValue = 0;
            
            if (workoutType === 'bike') {
                cadenceValue = data.instant_cadence || data.instantaneous_cadence || data.cadence || 0;
            } else if (workoutType === 'rower') {
                cadenceValue = data.stroke_rate || 0;
            }
            
            this.updateChartData(this.charts.cadence, cadenceValue, maxDataPoints);
        }
        
        // Batch update all charts
        this.batchUpdateCharts();
    }

    // Update button states based on connection and workout status
    updateButtonStates(deviceStatus, workoutActive) {
    const startWorkoutBtn = document.getElementById("start-workout-btn");
    const endWorkoutBtn = document.getElementById("end-workout-btn");

    if (startWorkoutBtn && endWorkoutBtn) {
        if (deviceStatus === "connected" && !workoutActive) {
            startWorkoutBtn.disabled = false;
            endWorkoutBtn.disabled = true;
        } else if (deviceStatus === "connected" && workoutActive) {
            startWorkoutBtn.disabled = true;
            endWorkoutBtn.disabled = false;
        } else {
            startWorkoutBtn.disabled = true;
            endWorkoutBtn.disabled = true;
        }
    }
}

}

// Initialize the WorkoutMonitor
const workoutMonitor = new WorkoutMonitor();

// Initial load of user preferences and start monitoring
workoutMonitor.loadUserPreferences().then(() => {
    workoutMonitor.startPolling(); // Start polling for status updates
});

// Initialize charts when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    workoutMonitor.initializeCharts();
});

// Expose workoutMonitor globally for debugging if needed
window.workoutMonitor = workoutMonitor;
