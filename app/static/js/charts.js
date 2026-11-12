(function () {
    function readJson(id) {
        var node = document.getElementById(id);
        if (!node) {
            return null;
        }
        try {
            return JSON.parse(node.textContent || "{}");
        } catch (error) {
            return null;
        }
    }

    function cssVar(name, fallback) {
        var value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return value || fallback;
    }

    function hexToRgba(hex, alpha) {
        var value = (hex || "").replace("#", "");
        if (value.length === 3) {
            value = value.split("").map(function (ch) { return ch + ch; }).join("");
        }
        if (value.length !== 6) {
            return hex;
        }
        var r = parseInt(value.slice(0, 2), 16);
        var g = parseInt(value.slice(2, 4), 16);
        var b = parseInt(value.slice(4, 6), 16);
        return "rgba(" + r + ", " + g + ", " + b + ", " + alpha + ")";
    }

    function palette() {
        var primary = cssVar("--primary", "#2563eb");
        return [primary, "#0f9f6e", "#7c3aed", "#f59e0b", "#e11d48", "#06b6d4"];
    }

    function hasValues(data) {
        return data && Array.isArray(data.values) && data.values.some(function (value) {
            return Number(value) > 0;
        });
    }

    function showEmpty(canvas, message) {
        var frame = canvas.closest(".chart-frame");
        if (!frame) {
            return;
        }
        canvas.classList.add("d-none");
        var note = document.createElement("p");
        note.className = "empty-copy chart-empty mb-0";
        note.textContent = message || "No chart data yet.";
        frame.appendChild(note);
    }

    function commonOptions(kind) {
        var text = cssVar("--text", "#12233d");
        var muted = cssVar("--muted", "#5b6b82");
        var grid = cssVar("--border", "#d7e4f7");
        var isRadial = kind === "pie" || kind === "doughnut";
        var isPolar = kind === "polarArea" || kind === "radar";
        var options = {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 700, easing: "easeOutQuart" },
            plugins: {
                legend: {
                    display: isRadial || isPolar,
                    position: "bottom",
                    labels: {
                        color: text,
                        boxWidth: 12,
                        padding: 16,
                        usePointStyle: true,
                        font: { family: "Plus Jakarta Sans", size: 12, weight: "600" }
                    }
                },
                tooltip: {
                    backgroundColor: cssVar("--heading", "#082f62"),
                    titleFont: { family: "Plus Jakarta Sans", weight: "700" },
                    bodyFont: { family: "Plus Jakarta Sans" },
                    padding: 12,
                    cornerRadius: 10
                }
            }
        };
        if (isRadial) {
            options.cutout = kind === "doughnut" ? "62%" : 0;
        } else if (isPolar) {
            options.scales = {
                r: {
                    beginAtZero: true,
                    ticks: { color: muted, backdropColor: "transparent", precision: 0, font: { family: "Plus Jakarta Sans" } },
                    grid: { color: grid },
                    angleLines: { color: grid }
                }
            };
        } else {
            options.plugins.legend.display = false;
            options.scales = {
                x: {
                    ticks: { color: muted, font: { family: "Plus Jakarta Sans", weight: "600" } },
                    grid: { display: false, borderColor: grid }
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: muted, precision: 0, font: { family: "Plus Jakarta Sans" } },
                    grid: { color: grid, borderDash: [4, 4] }
                }
            };
        }
        return options;
    }

    function datasetFor(type, data, colors) {
        var base = {
            label: data.label || "Count",
            data: data.values,
            backgroundColor: colors,
            borderWidth: 0
        };
        if (type === "bar") {
            return Object.assign(base, {
                backgroundColor: colors.map(function (color) { return hexToRgba(color, 0.82); }),
                borderRadius: 12,
                borderSkipped: false,
                maxBarThickness: 46
            });
        }
        if (type === "pie" || type === "doughnut") {
            return Object.assign(base, {
                borderColor: cssVar("--surface", "#ffffff"),
                borderWidth: 4,
                hoverOffset: 8
            });
        }
        if (type === "polarArea") {
            return Object.assign(base, {
                backgroundColor: colors.map(function (color) { return hexToRgba(color, 0.72); }),
                borderColor: colors,
                borderWidth: 2
            });
        }
        return base;
    }

    function makeChart(canvasId, type, data, emptyMessage) {
        var canvas = document.getElementById(canvasId);
        if (!canvas || typeof Chart === "undefined") {
            return;
        }
        if (!hasValues(data)) {
            showEmpty(canvas, emptyMessage);
            return;
        }
        var colors = palette().slice(0, data.labels.length);
        new Chart(canvas, {
            type: type,
            data: {
                labels: data.labels,
                datasets: [datasetFor(type, data, colors)]
            },
            options: commonOptions(type)
        });
    }

    var activity = readJson("activityChartData");
    var reminders = readJson("reminderChartData");
    makeChart("activityBarChart", "bar", activity, "Add medicines, appointments, or reports to see this bar chart.");
    makeChart("activityPieChart", "pie", activity, "Add health records to see the pie chart.");
    makeChart("activityDoughnutChart", "doughnut", activity, "Add health records to see this doughnut chart.");
    makeChart("reminderPolarChart", "polarArea", reminders, "Create reminders to see the polar chart.");
})();
