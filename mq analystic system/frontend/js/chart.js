let chartInstance = null;

function renderChart(data) {
    if (!data || typeof data !== "object") return;

    const ctx = document.getElementById("chart");

    if (chartInstance) {
        chartInstance.destroy();
    }

    const labels = Object.keys(data);
    const values = Object.values(data);

    chartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Result",
                data: values,
                backgroundColor: "rgba(59, 130, 246, 0.6)"
            }]
        }
    });
}