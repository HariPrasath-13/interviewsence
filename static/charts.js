/* ==========================================================================
   INTERVIEWSENSE CHART MANAGEMENT
   Wraps around Chart.js configurations, styles, dynamic updates, and
   clearing chart allocations.
   ========================================================================== */

let dashboardTimelineChart = null;
let dashboardDistributionChart = null;

let inspectTimelineChartInstance = null;
let inspectDistributionChartInstance = null;

// Palette definitions matching style.css theme
const CHART_COLOR_PALETTE = {
    happy: '#10b981',      // Emerald Green
    surprise: '#3b82f6',   // Blue
    neutral: '#6b7280',    // Gray/Slate
    sad: '#f59e0b',        // Warning Yellow/Amber
    angry: '#ef4444',      // Red
    fear: '#8b5cf6',       // Purple
    disgust: '#ec4899',     // Pink
    primaryGlow: 'rgba(79, 70, 229, 0.15)',
    gridLines: 'rgba(255, 255, 255, 0.05)',
    labels: '#94a3b8'
};

function formatTimerOffset(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// 1. Initialize Dashboard Charts
function initDashboardCharts() {
    const timelineCtx = document.getElementById('timelineChart');
    const distributionCtx = document.getElementById('distributionChart');
    
    if (!timelineCtx || !distributionCtx) return;
    
    // Timeline Chart setup
    dashboardTimelineChart = new Chart(timelineCtx.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Dominant Emotion Confidence',
                data: [],
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                borderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: [], // dynamic colors assigned per point
                fill: true,
                tension: 0.35
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const dataIndex = context.dataIndex;
                            const emotionDataset = context.chart.data.datasets[0];
                            const emotionTag = emotionDataset.pointEmotionTags ? emotionDataset.pointEmotionTags[dataIndex] : 'Neutral';
                            return `Confidence: ${context.raw.toFixed(1)}% (${emotionTag.toUpperCase()})`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: CHART_COLOR_PALETTE.gridLines },
                    ticks: { color: CHART_COLOR_PALETTE.labels }
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: CHART_COLOR_PALETTE.gridLines },
                    ticks: { color: CHART_COLOR_PALETTE.labels, callback: value => value + "%" }
                }
            }
        }
    });

    // Distribution Chart setup
    dashboardDistributionChart = new Chart(distributionCtx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Happy', 'Surprise', 'Neutral', 'Sad', 'Angry', 'Fear', 'Disgust'],
            datasets: [{
                data: [0, 0, 0, 0, 0, 0, 0],
                backgroundColor: [
                    CHART_COLOR_PALETTE.happy,
                    CHART_COLOR_PALETTE.surprise,
                    CHART_COLOR_PALETTE.neutral,
                    CHART_COLOR_PALETTE.sad,
                    CHART_COLOR_PALETTE.angry,
                    CHART_COLOR_PALETTE.fear,
                    CHART_COLOR_PALETTE.disgust
                ],
                borderWidth: 1,
                borderColor: '#121826'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: CHART_COLOR_PALETTE.labels, font: { size: 10 } }
                }
            },
            cutout: '70%'
        }
    });
}

// 2. Clear Dashboard Charts
function resetDashboardCharts() {
    if (dashboardTimelineChart) {
        dashboardTimelineChart.data.labels = [];
        dashboardTimelineChart.data.datasets[0].data = [];
        dashboardTimelineChart.data.datasets[0].pointBackgroundColor = [];
        dashboardTimelineChart.data.datasets[0].pointEmotionTags = [];
        dashboardTimelineChart.update();
    }
    
    if (dashboardDistributionChart) {
        dashboardDistributionChart.data.datasets[0].data = [0, 0, 0, 0, 0, 0, 0];
        dashboardDistributionChart.update();
    }
}

// 3. Update Live Dashboard Charts
function updateDashboardCharts(timelineList, distributionCounts) {
    if (!dashboardTimelineChart || !dashboardDistributionChart) return;
    
    // Smooth sample mapping (limit labels rendering spacing if too dense)
    const totalSamples = timelineList.length;
    let step = 1;
    if (totalSamples > 30) {
        step = Math.ceil(totalSamples / 30);
    }
    
    const labels = [];
    const confidences = [];
    const colors = [];
    const tags = [];
    
    for (let i = 0; i < totalSamples; i += step) {
        const item = timelineList[i];
        labels.push(formatTimerOffset(item.time));
        confidences.push(item.confidence);
        colors.push(CHART_COLOR_PALETTE[item.emotion.toLowerCase()] || '#6366f1');
        tags.push(item.emotion);
    }
    
    dashboardTimelineChart.data.labels = labels;
    dashboardTimelineChart.data.datasets[0].data = confidences;
    dashboardTimelineChart.data.datasets[0].pointBackgroundColor = colors;
    dashboardTimelineChart.data.datasets[0].pointEmotionTags = tags;
    dashboardTimelineChart.update();
    
    // Update distribution data
    const valuesKeys = ['happy', 'surprise', 'neutral', 'sad', 'angry', 'fear', 'disgust'];
    const totalCounts = valuesKeys.map(k => distributionCounts[k] || 0);
    
    dashboardDistributionChart.data.datasets[0].data = totalCounts;
    dashboardDistributionChart.update();
}

// 4. Render Inspection Charts inside History Frame View
function renderInspectionCharts(timelineId, distributionId, detailedTimeline, sessionAggregates) {
    const timelineCtx = document.getElementById(timelineId);
    const distributionCtx = document.getElementById(distributionId);
    
    if (!timelineCtx || !distributionCtx) return;
    
    // Destroy previous inspect charts allocations to prevent memory leaks and overlay overlays
    if (inspectTimelineChartInstance) {
        inspectTimelineChartInstance.destroy();
    }
    if (inspectDistributionChartInstance) {
        inspectDistributionChartInstance.destroy();
    }
    
    // Format dataset
    const labels = [];
    const confidences = [];
    const colors = [];
    const tags = [];
    
    // Limit displaying timeline details points
    const step = Math.max(1, Math.ceil(detailedTimeline.length / 32));
    
    for (let i = 0; i < detailedTimeline.length; i += step) {
        const d = detailedTimeline[i];
        labels.push(formatTimerOffset(d.elapsed_seconds));
        confidences.push(d.confidence);
        colors.push(CHART_COLOR_PALETTE[d.emotion.toLowerCase()] || '#6366f1');
        tags.push(d.emotion);
    }
    
    inspectTimelineChartInstance = new Chart(timelineCtx.getContext('2d'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Dominant Emotion Confidence',
                data: confidences,
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.08)',
                borderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: colors,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const index = context.dataIndex;
                            const emotionTag = tags[index];
                            return `Confidence: ${context.raw.toFixed(1)}% (${emotionTag.toUpperCase()})`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: CHART_COLOR_PALETTE.gridLines },
                    ticks: { color: CHART_COLOR_PALETTE.labels }
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: CHART_COLOR_PALETTE.gridLines },
                    ticks: { color: CHART_COLOR_PALETTE.labels, callback: value => value + "%" }
                }
            }
        }
    });
    
    // Build distribution counts from the details items
    const countsMap = { happy: 0, surprise: 0, neutral: 0, sad: 0, angry: 0, fear: 0, disgust: 0 };
    detailedTimeline.forEach(d => {
        const em = d.emotion.toLowerCase();
        if (em in countsMap) {
            countsMap[em]++;
        }
    });
    
    const distributionValues = ['happy', 'surprise', 'neutral', 'sad', 'angry', 'fear', 'disgust'].map(k => countsMap[k]);
    
    inspectDistributionChartInstance = new Chart(distributionCtx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Happy', 'Surprise', 'Neutral', 'Sad', 'Angry', 'Fear', 'Disgust'],
            datasets: [{
                data: distributionValues,
                backgroundColor: [
                    CHART_COLOR_PALETTE.happy,
                    CHART_COLOR_PALETTE.surprise,
                    CHART_COLOR_PALETTE.neutral,
                    CHART_COLOR_PALETTE.sad,
                    CHART_COLOR_PALETTE.angry,
                    CHART_COLOR_PALETTE.fear,
                    CHART_COLOR_PALETTE.disgust
                ],
                borderWidth: 1,
                borderColor: '#121826'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: CHART_COLOR_PALETTE.labels, font: { size: 9 } }
                }
            },
            cutout: '70%'
        }
    });
}
