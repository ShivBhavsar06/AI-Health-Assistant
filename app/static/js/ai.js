(function () {

    // =========================================================
    // MAIN ELEMENTS
    // =========================================================

    var composer = document.getElementById("aiComposer");
    if (!composer) {
        return;
    }

    var queryBox = document.getElementById("aiQuery");
    var conversation = document.getElementById("aiConversation");
    var emptyState = document.getElementById("aiEmptyState");
    var statusEl = document.getElementById("aiStatus");

    // Think mode
    var thinkToggle = document.getElementById("thinkToggle");
    var thinkToggleCompact = document.getElementById("thinkToggleCompact");

    // Voice
    var voiceStart = document.getElementById("voiceStart");
    var voiceSpeak = document.getElementById("voiceSpeak");

    // Attachment / report
    var attachButton = document.getElementById("aiAttach");
    var reportInput = document.getElementById("aiReport");
    var reportName = document.getElementById("aiReportName");
    var reportButton = document.getElementById("aiSummarizeReport");

    // PDF
    var pdfInput = document.getElementById("pdfResponse");
    var pdfButton = document.getElementById("pdfBtn");

    // Image
    var imageInput = document.getElementById("imageResponse");
    var imageButton = document.getElementById("imageBtn");


    // =========================================================
    // VARIABLES
    // =========================================================

    var recognition = null;

    var isSpeaking = false;
    var currentUtterance = null;

    var mode = "chat";
    var thinkEnabled = false;

    var lastResponse = "";
    var requestInFlight = false;


    // =========================================================
    // TRANSLATION
    // =========================================================

    function translate(message) {

        return window.translateAppText
            ? window.translateAppText(message)
            : message;
    }


    // =========================================================
    // STATUS
    // =========================================================

    function setStatus(message, state) {

        if (!statusEl) {
            return;
        }

        statusEl.textContent =
            translate(message || "");

        statusEl.className =
            "ai-status" +
            (state
                ? " ai-status-" + state
                : "");
    }


    // =========================================================
    // CSRF TOKEN
    // =========================================================

    function csrfToken() {

        var meta =
            document.querySelector(
                'meta[name="csrf-token"]'
            );

        var input =
            document.querySelector(
                'input[name="csrf_token"]'
            );

        return meta
            ? meta.getAttribute("content") || ""
            : input
                ? input.value
                : "";
    }


    // =========================================================
    // TIME
    // =========================================================

    function timestamp() {

        return new Intl.DateTimeFormat([], {
            hour: "numeric",
            minute: "2-digit"
        }).format(new Date());
    }


    // =========================================================
    // ESCAPE HTML
    // =========================================================

    function escapeHTML(text) {

        return String(text || "").replace(
            /[<>&"']/g,
            function (character) {

                return {
                    "<": "&lt;",
                    ">": "&gt;",
                    "&": "&amp;",
                    '"': "&quot;",
                    "'": "&#039;"
                }[character];

            }
        );
    }


    // =========================================================
    // ADD MESSAGE
    // =========================================================

    function addMessage(role, text, state) {

        if (emptyState) {

            emptyState.remove();

            emptyState = null;
        }


        var article =
            document.createElement("article");


        article.className =
            "ai-message ai-message-" +
            role +
            (state
                ? " ai-message-" + state
                : "");


        var label =
            document.createElement("span");

        label.className =
            "ai-message-label";

        label.textContent =
            role === "user"
                ? "You"
                : "HealthMate AI";


        var bubble =
            document.createElement("div");

        bubble.className =
            "ai-message-bubble";

        bubble.textContent =
            text;


        var time =
            document.createElement("time");

        time.className =
            "ai-message-time";

        time.textContent =
            timestamp();


        article.appendChild(label);
        article.appendChild(bubble);
        article.appendChild(time);


        conversation.appendChild(article);


        conversation.scrollTop =
            conversation.scrollHeight;
    }


    // =========================================================
    // TYPING INDICATOR
    // =========================================================

    function addTyping() {

        var existing =
            document.getElementById("aiTyping");

        if (existing) {
            return;
        }


        var typing =
            document.createElement("div");

        typing.className =
            "ai-typing";

        typing.id =
            "aiTyping";

        typing.setAttribute(
            "aria-label",
            "AI is thinking"
        );


        typing.innerHTML =
            "<span></span><span></span><span></span>";


        conversation.appendChild(typing);


        conversation.scrollTop =
            conversation.scrollHeight;
    }


    function removeTyping() {

        var typing =
            document.getElementById("aiTyping");

        if (typing) {
            typing.remove();
        }
    }


    // =========================================================
    // VOICE BUTTON
    // ONE BUTTON = SPEAK / STOP
    // =========================================================

    function updateVoiceButton() {

        if (!voiceSpeak) {
            return;
        }


        if (isSpeaking) {

            // ---------------------------------------------
            // SPEAKING → SHOW STOP
            // ---------------------------------------------

            voiceSpeak.innerHTML = `
                <i class="bi bi-stop-circle me-1"></i>
                Stop voice
            `;

            voiceSpeak.classList.add(
                "text-danger"
            );

            voiceSpeak.title =
                "Stop voice";

            voiceSpeak.setAttribute(
                "aria-label",
                "Stop voice"
            );

        } else {

            // ---------------------------------------------
            // NOT SPEAKING → SHOW SPEAK
            // ---------------------------------------------

            voiceSpeak.innerHTML = `
                <i class="bi bi-volume-up me-1"></i>
                Speak response
            `;

            voiceSpeak.classList.remove(
                "text-danger"
            );

            voiceSpeak.title =
                "Speak response";

            voiceSpeak.setAttribute(
                "aria-label",
                "Speak response"
            );
        }
    }


    // =========================================================
    // STOP SPEECH
    // =========================================================

    function stopSpeech() {

        if ("speechSynthesis" in window) {

            window.speechSynthesis.cancel();
        }


        isSpeaking = false;

        currentUtterance = null;


        updateVoiceButton();


        setStatus(
            "Voice stopped."
        );
    }


    // =========================================================
    // SPEAK RESPONSE
    // =========================================================

    function speakResponse() {

        if (!lastResponse) {
            return;
        }


        if (!("speechSynthesis" in window)) {

            setStatus(
                "Voice playback is not supported in this browser.",
                "error"
            );

            return;
        }


        // Stop previous speech
        window.speechSynthesis.cancel();


        currentUtterance =
            new SpeechSynthesisUtterance(
                lastResponse
            );


        // Voice settings
        currentUtterance.rate = 1;
        currentUtterance.pitch = 1;
        currentUtterance.volume = 1;


        // ---------------------------------------------
        // SPEECH STARTED
        // ---------------------------------------------

        currentUtterance.onstart =
            function () {

                isSpeaking = true;

                updateVoiceButton();

                setStatus(
                    "Speaking response...",
                    "busy"
                );
            };


        // ---------------------------------------------
        // SPEECH FINISHED
        // ---------------------------------------------

        currentUtterance.onend =
            function () {

                isSpeaking = false;

                currentUtterance = null;

                updateVoiceButton();

                setStatus(
                    "Response ready.",
                    "success"
                );
            };


        // ---------------------------------------------
        // SPEECH ERROR
        // ---------------------------------------------

        currentUtterance.onerror =
            function () {

                isSpeaking = false;

                currentUtterance = null;

                updateVoiceButton();

                setStatus(
                    "Voice playback stopped.",
                    "error"
                );
            };


        // Start speaking
        window.speechSynthesis.speak(
            currentUtterance
        );
    }


    // =========================================================
    // VOICE BUTTON CLICK
    // =========================================================

    if (voiceSpeak) {

        voiceSpeak.addEventListener(
            "click",
            function () {

                // -----------------------------------------
                // CURRENTLY SPEAKING → STOP
                // -----------------------------------------

                if (isSpeaking) {

                    stopSpeech();

                    return;
                }


                // -----------------------------------------
                // NOT SPEAKING → SPEAK
                // -----------------------------------------

                if (!lastResponse) {
                    return;
                }


                speakResponse();
            }
        );
    }


    // =========================================================
    // EXPORT STATE
    // =========================================================

    function setExportState(text) {

        lastResponse =
            text || "";


        // ---------------------------------------------
        // Stop previous speech when new response arrives
        // ---------------------------------------------

        if ("speechSynthesis" in window) {

            window.speechSynthesis.cancel();
        }


        isSpeaking = false;

        currentUtterance = null;


        updateVoiceButton();


        // ---------------------------------------------
        // PDF
        // ---------------------------------------------

        if (pdfInput) {

            pdfInput.value =
                lastResponse;
        }


        if (pdfButton) {

            pdfButton.disabled =
                !lastResponse;
        }


        // ---------------------------------------------
        // IMAGE
        // ---------------------------------------------

        if (imageInput) {

            imageInput.value =
                lastResponse;
        }


        if (imageButton) {

            imageButton.disabled =
                !lastResponse;
        }


        // ---------------------------------------------
        // SPEAK
        // ---------------------------------------------

        if (voiceSpeak) {

            voiceSpeak.disabled =
                !lastResponse ||
                !("speechSynthesis" in window);
        }
    }


    // =========================================================
    // THINK MODE
    // =========================================================

    function setThink(enabled) {

        thinkEnabled =
            enabled;


        [
            thinkToggle,
            thinkToggleCompact
        ].forEach(function (button) {

            if (!button) {
                return;
            }


            button.classList.toggle(
                "active",
                enabled
            );


            button.setAttribute(
                "aria-pressed",
                String(enabled)
            );

        });


        setStatus(
            enabled
                ? "Think mode enabled."
                : "Think mode off."
        );
    }


    // =========================================================
    // API RESPONSE
    // =========================================================

    function responseFrom(result) {

        return (
            result.data &&
            (
                result.data.response ||
                result.data.error
            )
        ) ||
        translate(
            "The AI assistant is temporarily unavailable. Please try again later."
        );
    }


    // =========================================================
    // SUBMIT QUERY
    // =========================================================

    function submitQuery(event) {

        if (event) {
            event.preventDefault();
        }


        if (requestInFlight) {
            return;
        }


        var query =
            (queryBox.value || "").trim();


        if (!query) {

            setStatus(
                "Please enter a health-related question.",
                "error"
            );

            queryBox.focus();

            return;
        }


        requestInFlight =
            true;


        // Add user message
        addMessage(
            "user",
            query
        );


        // Clear input
        queryBox.value =
            "";

        queryBox.style.height =
            "auto";


        // Clear previous response
        setExportState("");


        // Show typing
        addTyping();


        setStatus(
            thinkEnabled
                ? "Thinking deeply..."
                : "Thinking...",
            "busy"
        );


        // =====================================================
        // SEND TO FLASK BACKEND
        // =====================================================

        fetch(
            "/ai/query",
            {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json",

                    "X-CSRFToken":
                        csrfToken()
                },

                credentials:
                    "same-origin",

                body: JSON.stringify({
                    query: query,
                    mode: mode
                })
            }
        )


            // =================================================
            // RESPONSE
            // =================================================

            .then(function (response) {

                return response.json()
                    .then(function (data) {

                        return {
                            ok: response.ok,
                            data: data
                        };
                    });
            })


            // =================================================
            // PROCESS RESPONSE
            // =================================================

            .then(function (result) {

                var text =
                    responseFrom(result);


                removeTyping();


                addMessage(
                    "ai",
                    text,
                    result.ok
                        ? ""
                        : "error"
                );


                if (result.ok) {

                    // Save response for:
                    // PDF
                    // Image
                    // Voice

                    setExportState(
                        text
                    );


                    setStatus(
                        "Response ready.",
                        "success"
                    );

                } else {

                    setStatus(
                        "The assistant could not complete this request.",
                        "error"
                    );
                }
            })


            // =================================================
            // NETWORK ERROR
            // =================================================

            .catch(function () {

                removeTyping();


                var errorText =
                    translate(
                        "The AI assistant is temporarily unavailable. Please try again later."
                    );


                addMessage(
                    "ai",
                    errorText,
                    "error"
                );


                setStatus(
                    "Network error. Please try again.",
                    "error"
                );
            })


            // =================================================
            // FINALLY
            // =================================================

            .finally(function () {

                requestInFlight =
                    false;
            });
    }


    // =========================================================
    // FORM SUBMIT
    // =========================================================

    composer.addEventListener(
        "submit",
        submitQuery
    );


    // =========================================================
    // ENTER TO SEND
    // =========================================================

    queryBox.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Enter" &&
                !event.shiftKey &&
                !event.isComposing
            ) {

                event.preventDefault();

                submitQuery();
            }
        }
    );


    // =========================================================
    // TEXTAREA AUTO RESIZE
    // =========================================================

    queryBox.addEventListener(
        "input",
        function () {

            queryBox.style.height =
                "auto";


            queryBox.style.height =
                Math.min(
                    queryBox.scrollHeight,
                    140
                ) + "px";
        }
    );


    // =========================================================
    // THINK BUTTON
    // =========================================================

    [
        thinkToggle,
        thinkToggleCompact
    ].forEach(function (button) {

        if (!button) {
            return;
        }


        button.addEventListener(
            "click",
            function () {

                setThink(
                    !thinkEnabled
                );
            }
        );
    });


    // =========================================================
    // MODE BUTTONS
    // =========================================================

    document
        .querySelectorAll("[data-mode]")
        .forEach(function (button) {

            button.addEventListener(
                "click",
                function () {

                    mode =
                        button.getAttribute(
                            "data-mode"
                        ) || "chat";


                    document
                        .querySelectorAll(
                            "[data-mode]"
                        )
                        .forEach(
                            function (item) {

                                item.classList.toggle(
                                    "active",
                                    item === button
                                );
                            }
                        );


                    setStatus(
                        "Mode: " +
                        mode +
                        "."
                    );
                }
            );
        });


    // =========================================================
    // QUICK PROMPTS
    // =========================================================

    document
        .querySelectorAll("[data-prompt]")
        .forEach(function (button) {

            button.addEventListener(
                "click",
                function () {

                    queryBox.value =
                        button.getAttribute(
                            "data-prompt"
                        ) || "";


                    mode =
                        button.getAttribute(
                            "data-prompt-mode"
                        ) || "chat";


                    document
                        .querySelectorAll(
                            "[data-mode]"
                        )
                        .forEach(
                            function (item) {

                                item.classList.toggle(
                                    "active",
                                    item.getAttribute(
                                        "data-mode"
                                    ) === mode
                                );
                            }
                        );


                    queryBox.focus();


                    // Automatically send prompt
                    submitQuery();
                }
            );
        });


    // =========================================================
    // ATTACH REPORT
    // =========================================================

    if (
        attachButton &&
        reportInput
    ) {

        attachButton.addEventListener(
            "click",
            function () {

                reportInput.click();
            }
        );


        reportInput.addEventListener(
            "change",
            function () {

                var file =
                    reportInput.files &&
                    reportInput.files[0];


                if (!file) {

                    if (reportName) {
                        reportName.classList.add(
                            "d-none"
                        );
                    }


                    if (reportButton) {
                        reportButton.classList.add(
                            "d-none"
                        );
                    }

                    return;
                }


                if (reportName) {

                    var nameSpan =
                        reportName.querySelector(
                            "span"
                        );


                    if (nameSpan) {

                        nameSpan.textContent =
                            file.name;
                    }


                    reportName.classList.remove(
                        "d-none"
                    );
                }


                if (reportButton) {

                    reportButton.classList.remove(
                        "d-none"
                    );
                }


                setStatus(
                    "Report attached. Choose summarize report to continue."
                );
            }
        );
    }


    // =========================================================
    // SUMMARIZE REPORT
    // =========================================================

    if (
        reportButton &&
        reportInput
    ) {

        reportButton.addEventListener(
            "click",
            function () {

                var file =
                    reportInput.files &&
                    reportInput.files[0];


                if (!file) {

                    setStatus(
                        "Please choose a report to summarize.",
                        "error"
                    );

                    return;
                }


                var formData =
                    new FormData();


                formData.append(
                    "report",
                    file
                );


                reportButton.disabled =
                    true;


                addMessage(
                    "user",
                    "Summarize report: " +
                    file.name
                );


                addTyping();


                setStatus(
                    "Reading report...",
                    "busy"
                );


                fetch(
                    "/ai/summarize-report",
                    {

                        method: "POST",

                        headers: {
                            "X-CSRFToken":
                                csrfToken()
                        },

                        credentials:
                            "same-origin",

                        body: formData
                    }
                )


                    .then(function (response) {

                        return response.json()
                            .then(function (data) {

                                return {
                                    ok: response.ok,
                                    data: data
                                };
                            });
                    })


                    .then(function (result) {

                        var text =
                            responseFrom(result);


                        removeTyping();


                        addMessage(
                            "ai",
                            text,
                            result.ok
                                ? ""
                                : "error"
                        );


                        if (result.ok) {

                            setExportState(
                                text
                            );


                            setStatus(
                                "Report summary ready.",
                                "success"
                            );

                        } else {

                            setStatus(
                                text,
                                "error"
                            );
                        }
                    })


                    .catch(function () {

                        removeTyping();


                        addMessage(
                            "ai",
                            translate(
                                "The AI assistant is temporarily unavailable. Please try again later."
                            ),
                            "error"
                        );


                        setStatus(
                            "Network error. Please try again.",
                            "error"
                        );
                    })


                    .finally(function () {

                        reportButton.disabled =
                            false;
                    });
            }
        );
    }


    // =========================================================
    // SPEECH RECOGNITION
    // USER → AI
    // =========================================================

    var SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;


    if (
        voiceStart &&
        SpeechRecognition
    ) {

        recognition =
            new SpeechRecognition();


        recognition.lang =
            navigator.language ||
            "en-US";


        recognition.interimResults =
            false;


        recognition.maxAlternatives =
            1;


        // ---------------------------------------------
        // MICROPHONE CLICK
        // ---------------------------------------------

        voiceStart.addEventListener(
            "click",
            function () {

                setStatus(
                    "Listening...",
                    "busy"
                );


                try {

                    recognition.start();

                } catch (error) {

                    // Prevent "recognition has already started"
                    console.warn(
                        "Speech recognition:",
                        error
                    );
                }
            }
        );


        // ---------------------------------------------
        // SPEECH RESULT
        // ---------------------------------------------

        recognition.addEventListener(
            "result",
            function (event) {

                queryBox.value =
                    event.results[0][0]
                        .transcript;


                setStatus(
                    "Voice captured. Sending...",
                    "busy"
                );


                submitQuery();
            }
        );


        // ---------------------------------------------
        // START
        // ---------------------------------------------

        recognition.addEventListener(
            "start",
            function () {

                voiceStart.classList.add(
                    "active"
                );
            }
        );


        // ---------------------------------------------
        // END
        // ---------------------------------------------

        recognition.addEventListener(
            "end",
            function () {

                voiceStart.classList.remove(
                    "active"
                );
            }
        );


        // ---------------------------------------------
        // ERROR
        // ---------------------------------------------

        recognition.addEventListener(
            "error",
            function () {

                voiceStart.classList.remove(
                    "active"
                );


                setStatus(
                    "Voice input is unavailable. You can type your question instead.",
                    "error"
                );
            }
        );

    } else if (voiceStart) {

        voiceStart.disabled =
            true;


        voiceStart.title =
            "Voice input is not supported in this browser.";
    }


    // =========================================================
    // INITIAL VOICE BUTTON STATE
    // =========================================================

    updateVoiceButton();

})();


// baki  che aa 
function clearAttachedReport() {
    if (aiReport) {
        aiReport.value = '';
    }

    if (aiReportName) {
        aiReportName.classList.add('d-none');

        const nameSpan = aiReportName.querySelector('span');

        if (nameSpan) {
            nameSpan.textContent = '';
        }
    }

    if (aiSummarizeReport) {
        aiSummarizeReport.classList.add('d-none');
    }
}