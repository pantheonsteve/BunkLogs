/**
 * Self-rating trend over time for one scored category (Step 4_9 §4.4).
 *
 * The y-axis is pinned to the template's declared scale rather than fitted to
 * the data. Autoscaling would turn a 3→4 move on a 1–4 scale into a chart
 * that looks like a collapse-to-recovery, which is exactly the wrong story to
 * tell a teenager about their own self-assessment.
 *
 * Follows the growth dashboard's imperative canvas idiom (`chart.js/auto` +
 * destroy on dep change) rather than adding react-chartjs-2.
 */
import { useEffect, useRef } from 'react';
import { Chart as ChartJS } from 'chart.js';
import 'chart.js/auto';

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function RatingTrendChart({ series }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  const points = Array.isArray(series?.points) ? series.points : [];
  const scaleMin = series?.scale_min ?? 1;
  const scaleMax = series?.scale_max ?? 5;
  const label = series?.label || '';

  useEffect(() => {
    if (!canvasRef.current || points.length === 0) return undefined;
    if (chartRef.current) chartRef.current.destroy();

    chartRef.current = new ChartJS(canvasRef.current.getContext('2d'), {
      type: 'line',
      data: {
        labels: points.map((p) => formatDate(p.date)),
        datasets: [{
          label,
          data: points.map((p) => p.value),
          borderColor: 'rgb(124, 58, 237)',
          backgroundColor: 'rgba(124, 58, 237, 0.15)',
          pointRadius: 4,
          tension: 0.25,
          fill: true,
          // A single submission is a dot, not a line; without this it
          // renders as an invisible zero-length segment.
          showLine: points.length > 1,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            min: scaleMin,
            max: scaleMax,
            ticks: { stepSize: 1, precision: 0 },
            title: { display: true, text: `Scale ${scaleMin}–${scaleMax}` },
          },
          x: { grid: { display: false } },
        },
        plugins: { legend: { display: false } },
      },
    });

    return () => {
      chartRef.current?.destroy();
      chartRef.current = null;
    };
  }, [points, label, scaleMin, scaleMax]);

  if (points.length === 0) {
    return (
      <div data-testid={`trend-empty-${series?.trend_key || 'unknown'}`}>
        <p className="text-sm font-medium text-gray-900 dark:text-white">{label}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          No ratings yet — this fills in as you submit reflections.
        </p>
      </div>
    );
  }

  return (
    <div data-testid={`trend-chart-${series.trend_key}`}>
      <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">{label}</p>
      <div className="h-40">
        <canvas
          ref={canvasRef}
          role="img"
          aria-label={`${label}: ${points.length} rating${points.length === 1 ? '' : 's'} on a ${scaleMin} to ${scaleMax} scale`}
        />
      </div>
    </div>
  );
}
