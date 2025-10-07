async function getData() {
    const olt = document.getElementById("oltSelect").value;
    const port = document.getElementById("portInput").value;
    const threshold = document.getElementById("thresholdInput").value;

    const response = await fetch(`/api/low-rx?olt=${olt}&port=${port}&threshold=${threshold}`);
    const data = await response.json();

    const tbody = document.querySelector("#resultTable tbody");
    tbody.innerHTML = "";

    data.forEach(item => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${item.onu}</td>
            <td>${item.rx_power}</td>
            <td>${item.name}</td>
            <td>${item.description}</td>
        `;
        tbody.appendChild(tr);
    });
}
