/**
 * Enhanced Workout History and Statistics Display
 * Implements comprehensive filtering, search, detailed analysis, and comparison capabilities
 */

class WorkoutHistoryManager {
    constructor() {
        this.workouts = [];
        this.filteredWorkouts = [];
        this.selectedWorkouts = [];
        this.currentPage = 1;
        this.pageSize = 10;
        this.totalPages = 0;
        
        // Filter and search state
        this.filters = {
            dateRange: { start: null, end: null },
            workoutType: 'all',
            durationRange: { min: 0, max: 7200 }, // 0 to 2 hours
            distanceRange: { min: 0, max: 50000 }, // 0 to 50km
            search: ''
        };
        
        // Sort state
        this.sortBy = 'date-desc';
        
        // User preferences
        this.userUnitSystem = 'metric';
        
        // Charts for analysis
        this.analysisCharts = {};
        
        this.init();
    }
    
    init() {
        this.loadUserPreferences();
        this.setupEventListeners();
        this.loadWorkouts();
        console.log('WorkoutHistoryManager initialized');
    }
    
    async loadUserPreferences() {
        try {
            const response = await fetch('/api/settings');
            const data = await response.json();
            
            if (data.success && data.settings) {
                this.userUnitSystem = data.settings.unit_system || 'metric';
                this.pageSize = data.settings.history_page_size || 10;
            }
        } catch (error) {
            console.warn('Could not load user preferences:', error);
        }
    }
    
    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('workout-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce((e) => {
                this.filters.search = e.target.value;
                this.applyFilters();
            }, 300));
        }
        
        // Filter controls
        const workoutTypeFilter = document.getElementById('workout-type-filter');
        if (workoutTypeFilter) {
            workoutTypeFilter.addEventListener('change', (e) => {
                this.filters.workoutType = e.target.value;
                this.applyFilters();
            });
        }
        
        // Date range filters
        const startDateFilter = document.getElementById('start-date-filter');
        const endDateFilter = document.getElementById('end-date-filter');
        
        if (startDateFilter) {
            startDateFilter.addEventListener('change', (e) => {
                this.filters.dateRange.start = e.target.value ? new Date(e.target.value) : null;
                this.applyFilters();
            });
        }
        
        if (endDateFilter) {
            endDateFilter.addEventListener('change', (e) => {
                this.filters.dateRange.end = e.target.value ? new Date(e.target.value) : null;
                this.applyFilters();
            });
        }
        
        // Duration range slider
        const durationSlider = document.getElementById('duration-range-slider');
        if (durationSlider) {
            durationSlider.addEventListener('input', (e) => {
                const values = e.target.value.split(',');
                this.filters.durationRange.min = parseInt(values[0]);
                this.filters.durationRange.max = parseInt(values[1]);
                this.updateDurationRangeDisplay();
                this.applyFilters();
            });
        }
        
        // Sort controls
        const sortSelect = document.getElementById('sort-by');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.sortBy = e.target.value;
                this.applyFilters();
            });
        }
        
        // Pagination
        const prevPageBtn = document.getElementById('prev-page-btn');
        const nextPageBtn = document.getElementById('next-page-btn');
        
        if (prevPageBtn) {
            prevPageBtn.addEventListener('click', () => this.previousPage());
        }
        
        if (nextPageBtn) {
            nextPageBtn.addEventListener('click', () => this.nextPage());
        }
        
        // Export buttons
        const exportCsvBtn = document.getElementById('export-csv-btn');
        const exportJsonBtn = document.getElementById('export-json-btn');
        
        if (exportCsvBtn) {
            exportCsvBtn.addEventListener('click', () => this.exportData('csv'));
        }
        
        if (exportJsonBtn) {
            exportJsonBtn.addEventListener('click', () => this.exportData('json'));
        }
        
        // Comparison controls
        const compareBtn = document.getElementById('compare-workouts-btn');
        if (compareBtn) {
            compareBtn.addEventListener('click', () => this.showWorkoutComparison());
        }
        
        // Clear filters button
        const clearFiltersBtn = document.getElementById('clear-filters-btn');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => this.clearFilters());
        }
    }
    
    async loadWorkouts() {
        try {
            this.showLoading(true);
            
            const response = await fetch('/api/workouts?limit=1000'); // Load more workouts for better filtering
            const data = await response.json();
            
            if (data.success && data.workouts) {
                this.workouts = data.workouts.map(workout => {
                    // Ensure summary is parsed
                    if (workout.summary && typeof workout.summary === 'string') {
                        try {
                            workout.summary = JSON.parse(workout.summary);
                        } catch (e) {
                            console.error('Error parsing summary for workout', workout.id, e);
                            workout.summary = {};
                        }
                    }
                    return workout;
                });
                
                this.applyFilters();
                this.updateStatistics();
            } else {
                this.showError('Failed to load workout history');
            }
        } catch (error) {
            console.error('Error loading workouts:', error);
            this.showError('Error loading workout history: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    applyFilters() {
        let filtered = [...this.workouts];
        
        // Apply search filter
        if (this.filters.search) {
            const searchTerm = this.filters.search.toLowerCase();
            filtered = filtered.filter(workout => {
                const searchableText = [
                    workout.workout_type || '',
                    new Date(workout.start_time).toLocaleDateString(),
                    workout.summary?.notes || ''
                ].join(' ').toLowerCase();
                
                return searchableText.includes(searchTerm);
            });
        }
        
        // Apply workout type filter
        if (this.filters.workoutType !== 'all') {
            filtered = filtered.filter(workout => workout.workout_type === this.filters.workoutType);
        }
        
        // Apply date range filter
        if (this.filters.dateRange.start || this.filters.dateRange.end) {
            filtered = filtered.filter(workout => {
                const workoutDate = new Date(workout.start_time);
                
                if (this.filters.dateRange.start && workoutDate < this.filters.dateRange.start) {
                    return false;
                }
                
                if (this.filters.dateRange.end && workoutDate > this.filters.dateRange.end) {
                    return false;
                }
                
                return true;
            });
        }
        
        // Apply duration range filter
        filtered = filtered.filter(workout => {
            const duration = workout.duration || 0;
            return duration >= this.filters.durationRange.min && duration <= this.filters.durationRange.max;
        });
        
        // Apply distance range filter
        filtered = filtered.filter(workout => {
            const distance = (workout.summary && workout.summary.total_distance) || 0;
            return distance >= this.filters.distanceRange.min && distance <= this.filters.distanceRange.max;
        });
        
        // Apply sorting
        filtered = this.sortWorkouts(filtered, this.sortBy);
        
        this.filteredWorkouts = filtered;
        this.totalPages = Math.ceil(filtered.length / this.pageSize);
        this.currentPage = Math.min(this.currentPage, Math.max(1, this.totalPages));
        
        this.displayWorkouts();
        this.updatePagination();
        this.updateFilterSummary();
    }
    
    sortWorkouts(workouts, sortOption) {
        const [field, direction] = sortOption.split('-');
        const directionMultiplier = direction === 'asc' ? 1 : -1;
        
        return [...workouts].sort((a, b) => {
            let valueA, valueB;
            
            switch (field) {
                case 'date':
                    valueA = new Date(a.start_time).getTime();
                    valueB = new Date(b.start_time).getTime();
                    break;
                case 'duration':
                    valueA = a.duration || 0;
                    valueB = b.duration || 0;
                    break;
                case 'distance':
                    valueA = (a.summary && a.summary.total_distance) || 0;
                    valueB = (b.summary && b.summary.total_distance) || 0;
                    break;
                case 'calories':
                    valueA = (a.summary && a.summary.total_calories) || 0;
                    valueB = (b.summary && b.summary.total_calories) || 0;
                    break;
                case 'power':
                    valueA = (a.summary && a.summary.avg_power) || 0;
                    valueB = (b.summary && b.summary.avg_power) || 0;
                    break;
                default:
                    return 0;
            }
            
            return directionMultiplier * (valueA - valueB);
        });
    }
    
    displayWorkouts() {
        const workoutsList = document.getElementById('workouts-list');
        if (!workoutsList) return;
        
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const pageWorkouts = this.filteredWorkouts.slice(startIndex, endIndex);
        
        if (pageWorkouts.length === 0) {
            workoutsList.innerHTML = `
                <div class="alert alert-info">
                    <h5>No workouts found</h5>
                    <p>Try adjusting your filters or search terms.</p>
                </div>
            `;
            return;
        }
        
        let html = `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th><input type="checkbox" id="select-all-workouts"></th>
                            <th>Date</th>
                            <th>Type</th>
                            <th>Duration</th>
                            <th>Distance</th>
                            <th>Avg Power</th>
                            <th>Calories</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        pageWorkouts.forEach(workout => {
            const startTime = new Date(workout.start_time).toLocaleString();
            const workoutType = (workout.workout_type || 'Unknown').charAt(0).toUpperCase() + 
                              (workout.workout_type || 'Unknown').slice(1);
            const duration = this.formatDuration(workout.duration);
            
            // Format distance with unit conversion
            let distance = '-';
            if (workout.summary && workout.summary.total_distance) {
                const distanceM = parseFloat(workout.summary.total_distance);
                if (this.userUnitSystem === 'imperial') {
                    distance = `${this.convertDistance(distanceM, 'mi').toFixed(2)} mi`;
                } else {
                    distance = `${this.convertDistance(distanceM, 'km').toFixed(2)} km`;
                }
            }
            
            const avgPower = (workout.summary && workout.summary.avg_power) ? 
                           `${Math.round(workout.summary.avg_power)} W` : '-';
            const calories = (workout.summary && workout.summary.total_calories) ? 
                           `${Math.round(workout.summary.total_calories)} kcal` : '-';
            
            html += `
                <tr class="workout-row" data-workout-id="${workout.id}">
                    <td><input type="checkbox" class="workout-checkbox" value="${workout.id}"></td>
                    <td>${startTime}</td>
                    <td><span class="badge bg-primary">${workoutType}</span></td>
                    <td>${duration}</td>
                    <td>${distance}</td>
                    <td>${avgPower}</td>
                    <td>${calories}</td>
                    <td>
                        <div class="btn-group btn-group-sm" role="group">
                            <button class="btn btn-outline-primary view-btn" data-workout-id="${workout.id}" title="View Details">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn btn-outline-success fit-btn" data-workout-id="${workout.id}" title="Download FIT">
                                <i class="fas fa-download"></i>
                            </button>
                            <button class="btn btn-outline-danger delete-btn" data-workout-id="${workout.id}" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        workoutsList.innerHTML = html;
        
        // Add event listeners for the new elements
        this.setupWorkoutListEventListeners();
    }
    
    setupWorkoutListEventListeners() {
        // Select all checkbox
        const selectAllCheckbox = document.getElementById('select-all-workouts');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                const checkboxes = document.querySelectorAll('.workout-checkbox');
                checkboxes.forEach(checkbox => {
                    checkbox.checked = e.target.checked;
                });
                this.updateSelectedWorkouts();
            });
        }
        
        // Individual workout checkboxes
        const workoutCheckboxes = document.querySelectorAll('.workout-checkbox');
        workoutCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateSelectedWorkouts();
            });
        });
        
        // Action buttons
        const workoutsList = document.getElementById('workouts-list');
        if (workoutsList) {
            workoutsList.addEventListener('click', (e) => {
                const button = e.target.closest('button');
                if (!button) return;
                
                const workoutId = button.dataset.workoutId;
                if (!workoutId) return;
                
                if (button.classList.contains('view-btn')) {
                    this.viewWorkoutDetails(workoutId);
                } else if (button.classList.contains('fit-btn')) {
                    this.downloadFitFile(workoutId);
                } else if (button.classList.contains('delete-btn')) {
                    this.deleteWorkout(workoutId);
                }
            });
        }
    }
    
    updateSelectedWorkouts() {
        const checkboxes = document.querySelectorAll('.workout-checkbox:checked');
        this.selectedWorkouts = Array.from(checkboxes).map(cb => cb.value);
        
        // Update comparison button state
        const compareBtn = document.getElementById('compare-workouts-btn');
        if (compareBtn) {
            compareBtn.disabled = this.selectedWorkouts.length < 2;
            compareBtn.textContent = `Compare Workouts (${this.selectedWorkouts.length})`;
        }
        
        // Update bulk action buttons
        const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
        if (bulkDeleteBtn) {
            bulkDeleteBtn.disabled = this.selectedWorkouts.length === 0;
        }
    }
    
    async viewWorkoutDetails(workoutId) {
        try {
            const response = await fetch(`/api/workout/${workoutId}`);
            const data = await response.json();
            
            if (data.success && data.workout) {
                this.displayWorkoutAnalysis(data.workout);
            } else {
                this.showError('Failed to load workout details');
            }
        } catch (error) {
            console.error('Error loading workout details:', error);
            this.showError('Error loading workout details: ' + error.message);
        }
    }
    
    displayWorkoutAnalysis(workout) {
        const detailsContainer = document.getElementById('workout-details');
        if (!detailsContainer) return;
        
        // Create comprehensive workout analysis
        let html = `
            <div class="workout-analysis">
                <div class="row">
                    <div class="col-md-6">
                        <h5>Workout Overview</h5>
                        <div class="workout-overview">
                            <p><strong>Date:</strong> ${new Date(workout.start_time).toLocaleString()}</p>
                            <p><strong>Type:</strong> ${(workout.workout_type || 'Unknown').charAt(0).toUpperCase() + (workout.workout_type || 'Unknown').slice(1)}</p>
                            <p><strong>Duration:</strong> ${this.formatDuration(workout.duration)}</p>
                        </div>
                        
                        <h6>Performance Metrics</h6>
                        <div class="performance-metrics">
                            ${this.createMetricCard('Distance', this.formatDistance(workout.summary?.total_distance || 0), 'primary')}
                            ${this.createMetricCard('Avg Power', `${Math.round(workout.summary?.avg_power || 0)} W`, 'danger')}
                            ${this.createMetricCard('Max Power', `${Math.round(workout.summary?.max_power || 0)} W`, 'danger')}
                            ${this.createMetricCard('Avg HR', `${Math.round(workout.summary?.avg_heart_rate || 0)} bpm`, 'info')}
                            ${this.createMetricCard('Max HR', `${Math.round(workout.summary?.max_heart_rate || 0)} bpm`, 'info')}
                            ${this.createMetricCard('Calories', `${Math.round(workout.summary?.total_calories || 0)} kcal`, 'warning')}
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <h5>Workout Analysis</h5>
                        <div class="analysis-charts">
                            <canvas id="workout-analysis-chart" style="max-height: 300px;"></canvas>
                        </div>
                        
                        <div class="workout-zones mt-3">
                            <h6>Training Zones</h6>
                            <div id="training-zones-chart">
                                ${this.createTrainingZonesAnalysis(workout)}
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row mt-4">
                    <div class="col-12">
                        <h5>Detailed Metrics Chart</h5>
                        <div class="chart-container">
                            <canvas id="detailed-metrics-chart" style="height: 400px;"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        detailsContainer.innerHTML = html;
        
        // Create charts
        this.createWorkoutAnalysisCharts(workout);
    }
    
    createMetricCard(label, value, colorClass) {
        return `
            <div class="metric-card-small mb-2">
                <div class="card border-${colorClass}">
                    <div class="card-body p-2">
                        <div class="d-flex justify-content-between">
                            <span class="text-muted small">${label}</span>
                            <span class="fw-bold text-${colorClass}">${value}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    createTrainingZonesAnalysis(workout) {
        if (!workout.data_series || !workout.data_series.powers) {
            return '<p class="text-muted">No power data available for zone analysis</p>';
        }
        
        const powers = workout.data_series.powers.filter(p => p > 0);
        if (powers.length === 0) {
            return '<p class="text-muted">No valid power data for zone analysis</p>';
        }
        
        // Define power zones (these could be user-configurable)
        const zones = [
            { name: 'Recovery', min: 0, max: 100, color: '#28a745' },
            { name: 'Endurance', min: 100, max: 150, color: '#17a2b8' },
            { name: 'Tempo', min: 150, max: 200, color: '#ffc107' },
            { name: 'Threshold', min: 200, max: 250, color: '#fd7e14' },
            { name: 'VO2 Max', min: 250, max: 999, color: '#dc3545' }
        ];
        
        const zoneDistribution = zones.map(zone => {
            const timeInZone = powers.filter(p => p >= zone.min && p < zone.max).length;
            const percentage = (timeInZone / powers.length) * 100;
            return { ...zone, timeInZone, percentage };
        });
        
        let html = '<div class="training-zones">';
        zoneDistribution.forEach(zone => {
            if (zone.percentage > 0) {
                html += `
                    <div class="zone-bar mb-2">
                        <div class="d-flex justify-content-between mb-1">
                            <span class="small">${zone.name}</span>
                            <span class="small">${zone.percentage.toFixed(1)}%</span>
                        </div>
                        <div class="progress" style="height: 8px;">
                            <div class="progress-bar" style="width: ${zone.percentage}%; background-color: ${zone.color}"></div>
                        </div>
                    </div>
                `;
            }
        });
        html += '</div>';
        
        return html;
    }
    
    createWorkoutAnalysisCharts(workout) {
        if (!workout.data_series) return;
        
        // Create detailed metrics chart
        const ctx = document.getElementById('detailed-metrics-chart');
        if (ctx && workout.data_series.timestamps) {
            const timestamps = workout.data_series.timestamps.map((ts, index) => {
                return this.formatTimestamp(index); // Use index as seconds
            });
            
            const datasets = [];
            
            if (workout.data_series.powers && workout.data_series.powers.some(p => p > 0)) {
                datasets.push({
                    label: 'Power (W)',
                    data: workout.data_series.powers,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    yAxisID: 'yPower',
                    fill: false
                });
            }
            
            if (workout.data_series.heart_rates && workout.data_series.heart_rates.some(hr => hr > 0)) {
                datasets.push({
                    label: 'Heart Rate (bpm)',
                    data: workout.data_series.heart_rates,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    yAxisID: 'yHeartRate',
                    fill: false
                });
            }
            
            if (workout.data_series.cadences && workout.data_series.cadences.some(c => c > 0)) {
                datasets.push({
                    label: 'Cadence (RPM)',
                    data: workout.data_series.cadences,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    yAxisID: 'yCadence',
                    fill: false
                });
            }
            
            if (datasets.length > 0) {
                this.analysisCharts.detailed = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: timestamps,
                        datasets: datasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                title: { display: true, text: 'Time (MM:SS)' }
                            },
                            yPower: {
                                type: 'linear',
                                display: true,
                                position: 'left',
                                title: { display: true, text: 'Power (W)' }
                            },
                            yHeartRate: {
                                type: 'linear',
                                display: true,
                                position: 'right',
                                title: { display: true, text: 'Heart Rate (bpm)' },
                                grid: { drawOnChartArea: false }
                            },
                            yCadence: {
                                type: 'linear',
                                display: false,
                                position: 'right'
                            }
                        },
                        plugins: {
                            legend: { position: 'top' },
                            tooltip: {
                                mode: 'index',
                                intersect: false
                            }
                        }
                    }
                });
            }
        }
    }
    
    showWorkoutComparison() {
        if (this.selectedWorkouts.length < 2) {
            this.showError('Please select at least 2 workouts to compare');
            return;
        }
        
        const selectedWorkoutData = this.selectedWorkouts.map(id => 
            this.workouts.find(w => w.id == id)
        ).filter(w => w);
        
        this.displayWorkoutComparison(selectedWorkoutData);
    }
    
    displayWorkoutComparison(workouts) {
        const detailsContainer = document.getElementById('workout-details');
        if (!detailsContainer) return;
        
        let html = `
            <div class="workout-comparison">
                <h5>Workout Comparison (${workouts.length} workouts)</h5>
                
                <div class="comparison-table-container">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Metric</th>
                                ${workouts.map((w, i) => `<th>Workout ${i + 1}<br><small>${new Date(w.start_time).toLocaleDateString()}</small></th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><strong>Type</strong></td>
                                ${workouts.map(w => `<td>${(w.workout_type || 'Unknown').charAt(0).toUpperCase() + (w.workout_type || 'Unknown').slice(1)}</td>`).join('')}
                            </tr>
                            <tr>
                                <td><strong>Duration</strong></td>
                                ${workouts.map(w => `<td>${this.formatDuration(w.duration)}</td>`).join('')}
                            </tr>
                            <tr>
                                <td><strong>Distance</strong></td>
                                ${workouts.map(w => `<td>${this.formatDistance(w.summary?.total_distance || 0)}</td>`).join('')}
                            </tr>
                            <tr>
                                <td><strong>Avg Power</strong></td>
                                ${workouts.map(w => `<td>${Math.round(w.summary?.avg_power || 0)} W</td>`).join('')}
                            </tr>
                            <tr>
                                <td><strong>Max Power</strong></td>
                                ${workouts.map(w => `<td>${Math.round(w.summary?.max_power || 0)} W</td>`).join('')}
                            </tr>
                            <tr>
                                <td><strong>Avg Heart Rate</strong></td>
                                ${workouts.map(w => `<td>${Math.round(w.summary?.avg_heart_rate || 0)} bpm</td>`).join('')}
                            </tr>
                            <tr>
                                <td><strong>Calories</strong></td>
                                ${workouts.map(w => `<td>${Math.round(w.summary?.total_calories || 0)} kcal</td>`).join('')}
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <div class="comparison-charts mt-4">
                    <h6>Performance Comparison</h6>
                    <canvas id="comparison-chart" style="height: 300px;"></canvas>
                </div>
            </div>
        `;
        
        detailsContainer.innerHTML = html;
        
        // Create comparison chart
        this.createComparisonChart(workouts);
    }
    
    createComparisonChart(workouts) {
        const ctx = document.getElementById('comparison-chart');
        if (!ctx) return;
        
        const metrics = ['avg_power', 'max_power', 'avg_heart_rate', 'total_calories'];
        const metricLabels = ['Avg Power (W)', 'Max Power (W)', 'Avg HR (bpm)', 'Calories (kcal)'];
        
        const datasets = workouts.map((workout, index) => {
            const colors = [
                'rgba(255, 99, 132, 0.8)',
                'rgba(54, 162, 235, 0.8)',
                'rgba(75, 192, 192, 0.8)',
                'rgba(255, 206, 86, 0.8)',
                'rgba(153, 102, 255, 0.8)'
            ];
            
            return {
                label: `Workout ${index + 1} (${new Date(workout.start_time).toLocaleDateString()})`,
                data: metrics.map(metric => {
                    const value = workout.summary?.[metric] || 0;
                    return metric === 'total_calories' ? Math.round(value) : Math.round(value);
                }),
                backgroundColor: colors[index % colors.length],
                borderColor: colors[index % colors.length].replace('0.8', '1'),
                borderWidth: 2
            };
        });
        
        this.analysisCharts.comparison = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: metricLabels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top' }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 50
                        }
                    }
                }
            }
        });
    }
    
    async downloadFitFile(workoutId) {
        try {
            const response = await fetch(`/api/convert_fit/${workoutId}`, { method: 'POST' });
            const data = await response.json();
            
            if (data.success && data.fit_file_path) {
                const filename = data.fit_file_path.split(/[\\/]/).pop();
                window.location.href = `/fit_files/${filename}`;
                this.showNotification(`Downloading FIT file: ${filename}`, 'success');
            } else {
                this.showError(`Error preparing FIT file: ${data.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error downloading FIT file:', error);
            this.showError('Error downloading FIT file: ' + error.message);
        }
    }
    
    async deleteWorkout(workoutId) {
        if (!confirm('Are you sure you want to delete this workout? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/workout/${workoutId}`, { method: 'DELETE' });
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Workout deleted successfully', 'success');
                await this.loadWorkouts(); // Reload the list
                
                // Clear details if this workout was being viewed
                const detailsContainer = document.getElementById('workout-details');
                if (detailsContainer) {
                    detailsContainer.innerHTML = '<p>Select a workout to view details.</p>';
                }
            } else {
                this.showError(`Error deleting workout: ${data.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error deleting workout:', error);
            this.showError('Error deleting workout: ' + error.message);
        }
    }
    
    exportData(format) {
        if (this.filteredWorkouts.length === 0) {
            this.showError('No workouts to export');
            return;
        }
        
        const exportData = this.filteredWorkouts.map(workout => ({
            id: workout.id,
            date: workout.start_time,
            type: workout.workout_type,
            duration: workout.duration,
            distance: workout.summary?.total_distance || 0,
            avg_power: workout.summary?.avg_power || 0,
            max_power: workout.summary?.max_power || 0,
            avg_heart_rate: workout.summary?.avg_heart_rate || 0,
            max_heart_rate: workout.summary?.max_heart_rate || 0,
            calories: workout.summary?.total_calories || 0
        }));
        
        if (format === 'csv') {
            this.exportToCsv(exportData);
        } else if (format === 'json') {
            this.exportToJson(exportData);
        }
    }
    
    exportToCsv(data) {
        const headers = Object.keys(data[0]);
        const csvContent = [
            headers.join(','),
            ...data.map(row => headers.map(header => {
                const value = row[header];
                return typeof value === 'string' ? `"${value}"` : value;
            }).join(','))
        ].join('\n');
        
        this.downloadFile(csvContent, 'workout-history.csv', 'text/csv');
    }
    
    exportToJson(data) {
        const jsonContent = JSON.stringify(data, null, 2);
        this.downloadFile(jsonContent, 'workout-history.json', 'application/json');
    }
    
    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        this.showNotification(`Exported ${filename}`, 'success');
    }
    
    clearFilters() {
        // Reset all filters
        this.filters = {
            dateRange: { start: null, end: null },
            workoutType: 'all',
            durationRange: { min: 0, max: 7200 },
            distanceRange: { min: 0, max: 50000 },
            search: ''
        };
        
        // Reset UI elements
        const searchInput = document.getElementById('workout-search');
        if (searchInput) searchInput.value = '';
        
        const workoutTypeFilter = document.getElementById('workout-type-filter');
        if (workoutTypeFilter) workoutTypeFilter.value = 'all';
        
        const startDateFilter = document.getElementById('start-date-filter');
        if (startDateFilter) startDateFilter.value = '';
        
        const endDateFilter = document.getElementById('end-date-filter');
        if (endDateFilter) endDateFilter.value = '';
        
        // Reset sort
        this.sortBy = 'date-desc';
        const sortSelect = document.getElementById('sort-by');
        if (sortSelect) sortSelect.value = 'date-desc';
        
        // Reapply filters (which will show all workouts)
        this.applyFilters();
        
        this.showNotification('Filters cleared', 'info');
    }
    
    updateStatistics() {
        const statsContainer = document.getElementById('workout-statistics');
        if (!statsContainer) return;
        
        const totalWorkouts = this.workouts.length;
        const totalDistance = this.workouts.reduce((sum, w) => sum + (w.summary?.total_distance || 0), 0);
        const totalDuration = this.workouts.reduce((sum, w) => sum + (w.duration || 0), 0);
        const totalCalories = this.workouts.reduce((sum, w) => sum + (w.summary?.total_calories || 0), 0);
        
        const avgDistance = totalWorkouts > 0 ? totalDistance / totalWorkouts : 0;
        const avgDuration = totalWorkouts > 0 ? totalDuration / totalWorkouts : 0;
        
        // Get workout type distribution
        const typeDistribution = {};
        this.workouts.forEach(w => {
            const type = w.workout_type || 'Unknown';
            typeDistribution[type] = (typeDistribution[type] || 0) + 1;
        });
        
        let html = `
            <div class="statistics-grid">
                <div class="stat-card">
                    <h6>Total Workouts</h6>
                    <div class="stat-value">${totalWorkouts}</div>
                </div>
                <div class="stat-card">
                    <h6>Total Distance</h6>
                    <div class="stat-value">${this.formatDistance(totalDistance)}</div>
                </div>
                <div class="stat-card">
                    <h6>Total Time</h6>
                    <div class="stat-value">${this.formatDuration(totalDuration)}</div>
                </div>
                <div class="stat-card">
                    <h6>Total Calories</h6>
                    <div class="stat-value">${Math.round(totalCalories)} kcal</div>
                </div>
                <div class="stat-card">
                    <h6>Avg Distance</h6>
                    <div class="stat-value">${this.formatDistance(avgDistance)}</div>
                </div>
                <div class="stat-card">
                    <h6>Avg Duration</h6>
                    <div class="stat-value">${this.formatDuration(avgDuration)}</div>
                </div>
            </div>
            
            <div class="workout-types mt-3">
                <h6>Workout Types</h6>
                ${Object.entries(typeDistribution).map(([type, count]) => `
                    <div class="type-stat">
                        <span class="badge bg-primary">${type.charAt(0).toUpperCase() + type.slice(1)}</span>
                        <span class="count">${count} workouts</span>
                    </div>
                `).join('')}
            </div>
        `;
        
        statsContainer.innerHTML = html;
    }
    
    updatePagination() {
        const pageInfo = document.getElementById('page-info');
        const prevPageBtn = document.getElementById('prev-page-btn');
        const nextPageBtn = document.getElementById('next-page-btn');
        
        if (pageInfo) {
            pageInfo.textContent = `Page ${this.currentPage} of ${this.totalPages || 1} (${this.filteredWorkouts.length} workouts)`;
        }
        
        if (prevPageBtn) {
            prevPageBtn.disabled = this.currentPage <= 1;
        }
        
        if (nextPageBtn) {
            nextPageBtn.disabled = this.currentPage >= this.totalPages;
        }
    }
    
    updateFilterSummary() {
        const filterSummary = document.getElementById('filter-summary');
        if (!filterSummary) return;
        
        const activeFilters = [];
        
        if (this.filters.search) {
            activeFilters.push(`Search: "${this.filters.search}"`);
        }
        
        if (this.filters.workoutType !== 'all') {
            activeFilters.push(`Type: ${this.filters.workoutType}`);
        }
        
        if (this.filters.dateRange.start || this.filters.dateRange.end) {
            const start = this.filters.dateRange.start ? this.filters.dateRange.start.toLocaleDateString() : 'Any';
            const end = this.filters.dateRange.end ? this.filters.dateRange.end.toLocaleDateString() : 'Any';
            activeFilters.push(`Date: ${start} - ${end}`);
        }
        
        if (activeFilters.length > 0) {
            filterSummary.innerHTML = `
                <div class="alert alert-info">
                    <strong>Active Filters:</strong> ${activeFilters.join(', ')}
                    <button class="btn btn-sm btn-outline-secondary ms-2" onclick="workoutHistory.clearFilters()">Clear All</button>
                </div>
            `;
        } else {
            filterSummary.innerHTML = '';
        }
    }
    
    updateDurationRangeDisplay() {
        const display = document.getElementById('duration-range-display');
        if (display) {
            const min = this.formatDuration(this.filters.durationRange.min);
            const max = this.formatDuration(this.filters.durationRange.max);
            display.textContent = `${min} - ${max}`;
        }
    }
    
    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.displayWorkouts();
            this.updatePagination();
        }
    }
    
    nextPage() {
        if (this.currentPage < this.totalPages) {
            this.currentPage++;
            this.displayWorkouts();
            this.updatePagination();
        }
    }
    
    // Utility functions
    formatDuration(seconds) {
        if (!seconds) return '00:00:00';
        seconds = Math.round(seconds);
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    
    formatTimestamp(seconds) {
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
    
    formatDistance(meters) {
        if (!meters) return '0 km';
        
        if (this.userUnitSystem === 'imperial') {
            return `${this.convertDistance(meters, 'mi').toFixed(2)} mi`;
        } else {
            return `${this.convertDistance(meters, 'km').toFixed(2)} km`;
        }
    }
    
    convertDistance(meters, unit) {
        switch (unit) {
            case 'km':
                return meters / 1000;
            case 'mi':
                return meters / 1609.34;
            default:
                return meters;
        }
    }
    
    showLoading(show) {
        const loadingElement = document.getElementById('loading-indicator');
        if (loadingElement) {
            loadingElement.style.display = show ? 'block' : 'none';
        }
    }
    
    showError(message) {
        if (typeof showNotification === 'function') {
            showNotification(message, 'danger');
        } else {
            alert(message);
        }
    }
    
    showNotification(message, type = 'info') {
        if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
    
    debounce(func, wait) {
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
    
    // Public API
    getStatus() {
        return {
            totalWorkouts: this.workouts.length,
            filteredWorkouts: this.filteredWorkouts.length,
            selectedWorkouts: this.selectedWorkouts.length,
            currentPage: this.currentPage,
            totalPages: this.totalPages,
            activeFilters: this.filters
        };
    }
}

// Global instance
window.workoutHistory = new WorkoutHistoryManager();