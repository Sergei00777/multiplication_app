// Инициализация графиков
let accuracyChart, weeklyChart;

function initCharts() {
    const accuracyCtx = document.getElementById('accuracyChart').getContext('2d');
    const weeklyCtx = document.getElementById('weeklyChart').getContext('2d');

    accuracyChart = new Chart(accuracyCtx, {
        type: 'bar',
        data: {
            labels: ['2', '3', '4', '5', '6', '7', '8', '9'],
            datasets: [{
                label: 'Точность %',
                data: [],
                backgroundColor: 'rgba(102, 126, 234, 0.8)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Точность %'
                    }
                }
            }
        }
    });

    weeklyChart = new Chart(weeklyCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Точность за неделю',
                data: [],
                borderColor: 'rgba(255, 107, 107, 1)',
                backgroundColor: 'rgba(255, 107, 107, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Точность %'
                    }
                }
            }
        }
    });
}

// Загрузка данных статистики
async function loadStats() {
    try {
        const [dailyStats, weeklyProgress, overallStats, achievements] = await Promise.all([
            fetch('/api/daily_stats').then(r => r.json()),
            fetch('/api/weekly_progress').then(r => r.json()),
            fetch('/api/overall_stats').then(r => r.json()),
            fetch('/api/achievements').then(r => r.json())
        ]);

        updateCharts(dailyStats, weeklyProgress);
        updateOverallStats(overallStats);
        updateAchievements(achievements);
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
    }
}

function updateCharts(dailyStats, weeklyProgress) {
    // Обновляем график точности по числам
    const accuracyData = Array(8).fill(0);
    dailyStats.forEach(stat => {
        accuracyData[stat.number - 2] = stat.accuracy;
    });
    accuracyChart.data.datasets[0].data = accuracyData;
    accuracyChart.update();

    // Обновляем недельный прогресс
    weeklyChart.data.labels = weeklyProgress.map(day =>
        new Date(day.date).toLocaleDateString('ru-RU', { weekday: 'short' })
    );
    weeklyChart.data.datasets[0].data = weeklyProgress.map(day => day.accuracy);
    weeklyChart.update();
}