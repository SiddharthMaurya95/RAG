async function runPipeline() {
    const query = document.getElementById("query").value;
    const fileInput = document.getElementById("fileInput").files[0];

    if (!query || !fileInput) {
        alert("Upload file and enter query");
        return;
    }

    let formData = new FormData();
    formData.append("query", query);
    formData.append("file", fileInput);

    try {
        const res = await fetch("http://127.0.0.1:8000/run", {
            method: "POST",
            body: formData
        });

        let text = await res.text();
        console.log("RAW:", text);

        let data = JSON.parse(text);

        // ✅ Show result
        document.getElementById("result").innerText =
            JSON.stringify(data.result, null, 2);

        // ✅ Show code
        document.getElementById("codeBox").innerText =
            data.code;

        // ✅ Insights
        document.getElementById("insights").innerText =
            data.insights;

        // ✅ Summary
        document.getElementById("summary").innerText =
            data.summary || "";

        // ✅ Chart
        renderChart(data.result);

    } catch (err) {
        console.error(err);
        alert("Error connecting to backend");
    }
}

// ✅ File preview (like Streamlit dataframe preview)
document.getElementById("fileInput").addEventListener("change", function () {
    const file = this.files[0];

    if (!file) return;

    const reader = new FileReader();

    reader.onload = function (e) {
        const text = e.target.result;
        const rows = text.split("\n").slice(0, 5);
        document.getElementById("preview").innerText = rows.join("\n");
    };

    reader.readAsText(file);
});