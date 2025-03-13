import React from 'react';
import { Line } from 'react-chartjs-2';
import type { ChartDataset } from 'chart.js';

export interface LineChartData {
    labels: string[];
    datasets: ChartDataset<'line', (number | null)[]>[];
}

interface LineScenarioChartProps {
    data: LineChartData;
}

const chartColor = '#a7a7a7';

const LineScenarioChart: React.FC<LineScenarioChartProps> = ({ data }) => {
    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { position: 'top' as const },
            title: { display: true, text: 'Wykres scenariusza - linia', color: chartColor },
        },
        scales: {
            x: {
                title: { display: true, text: 'Rozmiar' },
                ticks: { color: chartColor },
                grid: { color: chartColor }
            },
            y: {
                title: { display: true, text: 'Wartość' },
                ticks: { color: chartColor },
                grid: { color: chartColor }
            },
        },
    };

    return (
        <div className="line-chart" style={{ height: '400px' }}>
            <Line data={data} options={options} />
        </div>
    );
};

export default LineScenarioChart;
