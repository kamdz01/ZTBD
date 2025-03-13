import React from 'react';
import { Bar } from 'react-chartjs-2';
import { type ChartDataset } from 'chart.js';

export interface BarChartData {
    labels: string[];
    datasets: ChartDataset<'bar', (number | null)[]>[];
}

interface BarScenarioChartProps {
    data: BarChartData;
}

const chartColor = '#a7a7a7';

const BarScenarioChart: React.FC<BarScenarioChartProps> = ({ data }) => {
    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { position: 'top' as const },
            title: { display: true, text: 'Wykres scenariusza - słupki', color: chartColor },
        },
        scales: {
            x: {
                title: { display: true, text: 'Rozmiar' },
                ticks: { color: chartColor },
                grid: { color: chartColor },
            },
            y: {
                title: { display: true, text: 'Wartość' },
                ticks: { color: chartColor },
                grid: { color: chartColor },
            },
        },
    };

    return (
        <div className="bar-chart" style={{ height: '400px' }}>
            <Bar data={data} options={options} />
        </div>
    );
};

export default BarScenarioChart;
