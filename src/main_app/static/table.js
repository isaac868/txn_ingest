var categories = JSON.parse(document.getElementById("options").textContent)
var categoryNames = categories.map(tuple => tuple[1])
var categoryMap = new Map()
for (category of categories) {
    categoryMap.set(category[1], category[0])
}
var table = new Tabulator("#txn-table", {
    dependencies: {
        DateTime: luxon.DateTime,
    },
    height: "90vh",
    index: "idx",
    ajaxURL: pageUrl,
    ajaxParams: { getTxnData: "True" },
    movableRows: false,
    rowHeader: { formatter: "rowSelection", titleFormatter: "plaintext", title: rowSelectTitle, hozAlign: "center", headerSort: false, resizable: false },
    selectableRowsRangeMode: "click",
    layout: "fitData",
    columns: [
        {
            title: "Date", field: "date", formatter: "datetime", formatterParams: {
                inputFormat: "iso",
                outputFormat: "yyyy-MM-dd",
                invalidPlaceholder: "(invalid date)",
                timezone: "America/Los_Angeles",
            }
        },
        { title: "Account", field: "accnt", sorter: "string" },
        { title: "Description", field: "desc", sorter: "string" },
        { title: "Amount", field: "amnt", sorter: "number" },
        {
            title: "Category", field: "cat", sorter: "string", editor: "list", validator: "required", editorParams: {
                values: categoryNames,
                allowEmpty: false,
            }
        },
        { title: "Category Override", field: "cat_o", sorter: "boolean", formatter: "tickCross", editor: true },
    ],
});

// Enable bootstrap tooltips
const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))

table.on("cellEdited", function (cell) {
    if (cell.getField() == "cat") {
        cell.getRow().update({ "cat_o": true })
    }
    if (cell.getField() == "cat_o") {
        cell.getRow().getCell("cat").restoreInitialValue()
    }
});

async function handleResponse(response) {
    if (response.ok) {
        window.location.href = response.url
    } else {
        console.error("Response status: " + response.status);
    }
}

async function confirmChanges() {
    var deletedRowIndices = table.getSelectedRows().map(row => Number(row.getIndex()))
    var editedRows = table.getEditedCells().map(cell => cell.getRow())
    var uniqueEditedRows = []
    for (row of editedRows) {
        var uniqueRowIndices = uniqueEditedRows.map(row => row.getIndex())
        var rowIndex = row.getIndex()
        if (!uniqueRowIndices.includes(rowIndex) && !deletedRowIndices.includes(rowIndex)) {
            uniqueEditedRows.push(row)
        }
    }

    var formattedChanges = uniqueEditedRows.reduce((acc, row) => {
        const index = row.getIndex();
        acc[index] = {
            category: categoryMap.get(row.getCell("cat").getValue()),
            override: row.getCell("cat_o").getValue()
        };
        return acc;
    }, {});

    const response = await fetch(pageUrl, {
        method: "POST",
        body: JSON.stringify({ changes: formattedChanges, deleted: deletedRowIndices }),
        headers: {
            "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
            "Content-Type": "application/json",
        }
    })

    handleResponse(response)
}

async function cancelChanges() {
    const response = await fetch(pageUrl, {
        method: "POST",
        body: JSON.stringify({ cancel: true }),
        headers: {
            "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
            "Content-Type": "application/json",
        }
    })

    handleResponse(response)
}