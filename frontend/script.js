document.addEventListener("DOMContentLoaded", () => {

    const fileInput = document.getElementById("fileInput");
    const codeArea = document.getElementById("codeArea");
    const analyzeBtn = document.getElementById("analyzeBtn");
    const status = document.getElementById("status");
    const result = document.getElementById("result");
    const resultCard = document.getElementById("resultCard");

    //---------------------------------------------------------
    // Read uploaded file
    //---------------------------------------------------------

    fileInput.addEventListener("change", async (e) => {

        const file = e.target.files[0];

        if (!file) return;

        try {

            codeArea.value = await file.text();

            status.textContent = `Loaded ${file.name}`;

            result.innerHTML = "";

            resultCard.classList.add("hidden");

        } catch {

            status.textContent = "Unable to read selected file.";

        }

    });

    //---------------------------------------------------------
    // Analyze button
    //---------------------------------------------------------

    analyzeBtn.addEventListener("click", async () => {

        const code = codeArea.value.trim();

        if (!code) {

            status.textContent =
                "Please paste code or upload a source file.";

            return;

        }

        analyzeBtn.disabled = true;

        status.innerHTML =
            "Analyzing code... <span class='spinner'></span>";

        result.innerHTML = "";

        resultCard.classList.add("hidden");

        try {

            const response = await fetch("/analyze", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    code: code
                })

            });

            const data = await response.json();

            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    data.error ||
                    "Unknown server error"
                );

            }

            //-----------------------------------------------------
            // Clean response
            //-----------------------------------------------------

            let markdown = cleanAgentResponse(data.result);

            //-----------------------------------------------------
            // Convert Markdown -> HTML
            //-----------------------------------------------------

            result.innerHTML = marked.parse(markdown);

            resultCard.classList.remove("hidden");

            status.textContent = "Analysis complete.";

        }

        catch (err) {

            result.innerHTML = `
                <div class="error-box">
                    <h3>Analysis Failed</h3>
                    <pre>${escapeHtml(err.message)}</pre>
                </div>
            `;

            resultCard.classList.remove("hidden");

            status.textContent = "Error.";

        }

        finally {

            analyzeBtn.disabled = false;

        }

    });

});


//=============================================================
// Remove streamed event metadata
//=============================================================

function cleanAgentResponse(text) {

    if (!text) return "";

    //---------------------------------------------------------
    // Remove common event metadata
    //---------------------------------------------------------

    text = text.replace(/"thought_signature":[\s\S]*?"actions"/g, "");

    text = text.replace(/"artifact_delta":[\s\S]*?"timestamp":[^,}]+/g, "");

    text = text.replace(/"requested_auth_configs":[\s\S]*?\}/g, "");

    text = text.replace(/"requested_tool_confirmations":[\s\S]*?\}/g, "");

    //---------------------------------------------------------
    // Find beginning of actual response
    //---------------------------------------------------------

    const markers = [

        "# ",

        "## ",

        "**",

        "The provided code",

        "Overall Assessment",

        "Syntax",

        "Summary",

        "Recommendations"

    ];

    let first = -1;

    for (const m of markers) {

        const index = text.indexOf(m);

        if (index >= 0) {

            if (first === -1 || index < first) {

                first = index;

            }

        }

    }

    if (first >= 0) {

        text = text.substring(first);

    }

    //---------------------------------------------------------

    return text.trim();

}


//=============================================================
// Escape HTML for errors
//=============================================================

function escapeHtml(str) {

    return str.replace(/[&<>"']/g, function (m) {

        return ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            "\"": "&quot;",
            "'": "&#039;"
        })[m];

    });

}