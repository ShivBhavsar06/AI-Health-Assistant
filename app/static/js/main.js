document.addEventListener("DOMContentLoaded", function () {
    initValidatedForms();
    initPasswordToggles();
    initThemeControls();
    initLanguageControls();
    initSidebarToggle();
    initSettingsSearch();
    initPhoneInputs();
    initProfileEdit();

    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            var message = form.getAttribute("data-confirm") || "Are you sure?";
            if (window.translateAppText) {
                message = window.translateAppText(message);
            }
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll(".alert.alert-dismissible").forEach(function (alertEl) {
        window.setTimeout(function () {
            if (typeof bootstrap !== "undefined") {
                bootstrap.Alert.getOrCreateInstance(alertEl).close();
            } else {
                alertEl.remove();
            }
        }, 3000);
    });

    var menubar = document.querySelector(".app-menubar");
    if (menubar) {
        var syncMenubar = function () {
            menubar.classList.toggle("is-scrolled", window.scrollY > 8);
        };
        syncMenubar();
        window.addEventListener("scroll", syncMenubar, { passive: true });
    }

    var navCollapse = document.getElementById("mainNav");
    if (navCollapse) {
        navCollapse.querySelectorAll(".nav-link, .btn").forEach(function (link) {
            link.addEventListener("click", function () {
                if (window.matchMedia && window.matchMedia("(max-width: 991px)").matches && typeof bootstrap !== "undefined") {
                    bootstrap.Collapse.getOrCreateInstance(navCollapse, { toggle: false }).hide();
                }
            });
        });
    }

    if (document.body.getAttribute("data-reminders") === "1") {
        initReminderNotifications();
    }
});

function initValidatedForms() {
    document.querySelectorAll(".validated-form").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            var password = form.querySelector('input[name="password"]');
            var confirm = form.querySelector('input[name="confirm_password"]');
            if (password && confirm && confirm.value && password.value !== confirm.value) {
                confirm.setCustomValidity("Passwords do not match.");
            } else if (confirm) {
                confirm.setCustomValidity("");
            }
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add("was-validated");
        });
    });
}

function initPhoneInputs() {
    document.querySelectorAll("[data-phone-input]").forEach(function (input) {
        input.addEventListener("input", function () {
            input.value = (input.value || "").replace(/\D/g, "").slice(0, 10);
        });
    });
}

function initProfileEdit() {
    var form = document.getElementById("editProfile");
    if (!form) {
        return;
    }
    var open = function () {
        form.classList.remove("d-none");
        form.scrollIntoView({ behavior: "smooth", block: "start" });
        var first = form.querySelector("input, select, textarea");
        if (first) {
            first.focus();
        }
    };
    document.querySelectorAll("[data-profile-edit-open]").forEach(function (button) {
        button.addEventListener("click", open);
    });
    document.querySelectorAll("[data-profile-edit-cancel]").forEach(function (button) {
        button.addEventListener("click", function () {
            form.classList.add("d-none");
        });
    });
    var photoInput = form.querySelector("[data-profile-photo-input]");
    var photo = document.querySelector(".profile-photo");
    if (photoInput) {
        photoInput.addEventListener("change", function () {
            var file = photoInput.files && photoInput.files[0];
            if (!file || !file.type.startsWith("image/")) {
                return;
            }
            var url = URL.createObjectURL(file);
            if (photo) {
                photo.src = url;
            } else {
                var placeholder = document.querySelector(".profile-photo-placeholder");
                if (placeholder) {
                    var image = document.createElement("img");
                    image.className = "profile-photo";
                    image.alt = "Profile photo";
                    image.src = url;
                    placeholder.replaceWith(image);
                }
            }
            open();
        });
    }
}

function initPasswordToggles() {
    document.querySelectorAll(".password-toggle").forEach(function (button) {
        button.addEventListener("click", function () {
            var input = button.closest(".password-field").querySelector("input");
            var icon = button.querySelector("i");
            var showing = input.type === "text";
            input.type = showing ? "password" : "text";
            button.setAttribute("aria-label", showing ? "Show password" : "Hide password");
            button.setAttribute("title", showing ? "Show password" : "Hide password");
            if (icon) {
                icon.className = showing ? "bi bi-eye" : "bi bi-eye-slash";
            }
        });
    });
}

function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.setAttribute("data-bs-theme", theme);
}

function initThemeControls() {
    var theme = localStorage.getItem("aihealth.theme") || "light";
    var accent = localStorage.getItem("aihealth.accent") || "#2563eb";
    applyTheme(theme);
    document.documentElement.style.setProperty("--primary", accent);

    document.querySelectorAll("[data-theme-choice]").forEach(function (button) {
        button.classList.toggle("active", button.getAttribute("data-theme-choice") === theme);
        button.addEventListener("click", function () {
            theme = button.getAttribute("data-theme-choice") || "light";
            localStorage.setItem("aihealth.theme", theme);
            applyTheme(theme);
            document.querySelectorAll("[data-theme-choice]").forEach(function (item) {
                item.classList.toggle("active", item === button);
            });
        });
    });

    document.querySelectorAll("[data-accent-choice]").forEach(function (button) {
        button.classList.toggle("active", button.getAttribute("data-accent-choice") === accent);
        button.addEventListener("click", function () {
            accent = button.getAttribute("data-accent-choice") || "#2563eb";
            localStorage.setItem("aihealth.accent", accent);
            document.documentElement.style.setProperty("--primary", accent);
            document.querySelectorAll("[data-accent-choice]").forEach(function (item) {
                item.classList.toggle("active", item === button);
            });
        });
    });
}

function initLanguageControls() {
    var language = localStorage.getItem("aihealth.language") || "en";
    document.documentElement.lang = language;
    var choice = document.getElementById("languageChoice");
    if (choice) {
        choice.value = language;
        choice.addEventListener("change", function () {
            localStorage.setItem("aihealth.language", choice.value);
            window.location.reload();
        });
    }
    if (language === "en") {
        return;
    }
    var dictionaries = {
        hi: {
            "Dashboard": "डैशबोर्ड", "Home": "होम", "Features": "सुविधाएं", "About": "परिचय", "Users": "उपयोगकर्ता", "Health": "स्वास्थ्य", "Medicines": "दवाइयां", "Reminders": "रिमाइंडर", "Appointments": "अपॉइंटमेंट", "Reports": "रिपोर्ट", "Medical reports": "मेडिकल रिपोर्ट", "Assistant": "सहायक", "Profile": "प्रोफ़ाइल", "Settings": "सेटिंग्स", "Feedback": "प्रतिक्रिया", "Login": "लॉग इन", "Logout": "लॉग आउट", "Get started": "शुरू करें", "Create account": "खाता बनाएं", "Welcome back": "वापसी पर स्वागत है", "Overview": "अवलोकन", "Preferences": "प्राथमिकताएं", "Personal health": "व्यक्तिगत स्वास्थ्य", "Workspace": "कार्यस्थल", "Admin": "व्यवस्थापक", "Patient profile": "रोगी प्रोफ़ाइल", "Today's medicine reminders": "आज की दवा के रिमाइंडर", "Upcoming appointments": "आगामी अपॉइंटमेंट", "AI Health Assistant": "एआई स्वास्थ्य सहायक", "Ask the assistant": "सहायक से पूछें", "View all": "सभी देखें", "Manage": "प्रबंधित करें", "Language": "भाषा", "App language": "ऐप भाषा", "Display mode": "डिस्प्ले मोड", "Light": "लाइट", "Dark": "डार्क", "Accent color": "मुख्य रंग", "Interface color": "इंटरफ़ेस रंग", "Health activity": "स्वास्थ्य गतिविधि", "Delete account": "खाता हटाएं", "Close": "बंद करें", "Save": "सहेजें", "Save changes": "परिवर्तन सहेजें", "Edit profile": "प्रोफ़ाइल संपादित करें", "Search settings": "सेटिंग्स खोजें", "No matching settings found.": "कोई मिलती हुई सेटिंग नहीं मिली।", "Blood group": "रक्त समूह", "Pending reminders": "लंबित रिमाइंडर", "No medicine reminders for today.": "आज के लिए कोई दवा रिमाइंडर नहीं है।", "No upcoming appointments.": "कोई आगामी अपॉइंटमेंट नहीं है।", "Doctor": "डॉक्टर", "When": "कब", "Status": "स्थिति", "Medicine": "दवा", "Time": "समय", "General health information only, not a diagnosis.": "केवल सामान्य स्वास्थ्य जानकारी, निदान नहीं।", "This assistant provides general health information only. It does not replace professional medical care. Seek emergency services for serious symptoms.": "यह सहायक केवल सामान्य स्वास्थ्य जानकारी देता है। यह पेशेवर चिकित्सा सेवा का विकल्प नहीं है। गंभीर लक्षणों पर आपातकालीन सेवा लें।", "Chat": "चैट", "Recommendations": "सुझाव", "Health summary": "स्वास्थ्य सारांश", "Your question": "आपका प्रश्न", "Send": "भेजें", "Voice": "आवाज़", "Speak response": "उत्तर सुनें", "Export PDF": "PDF निर्यात करें", "Quick prompts": "त्वरित प्रश्न", "Voice assistant": "आवाज़ सहायक", "Response ready.": "उत्तर तैयार है।", "Are you sure?": "क्या आप निश्चित हैं?", "Date of birth": "जन्म तिथि", "Gender": "लिंग", "Full name": "पूरा नाम", "Username": "उपयोगकर्ता नाम", "Email": "ईमेल", "Phone": "फ़ोन", "Password": "पासवर्ड", "Confirm password": "पासवर्ड की पुष्टि करें", "Delete account": "खाता हटाएं"
        },
        gu: {
            "Dashboard": "ડેશબોર્ડ", "Home": "હોમ", "Features": "સુવિધાઓ", "About": "વિશે", "Users": "વપરાશકર્તાઓ", "Health": "આરોગ્ય", "Medicines": "દવાઓ", "Reminders": "રિમાઇન્ડર", "Appointments": "મુલાકાતો", "Reports": "રિપોર્ટ્સ", "Medical reports": "મેડિકલ રિપોર્ટ્સ", "Assistant": "સહાયક", "Profile": "પ્રોફાઇલ", "Settings": "સેટિંગ્સ", "Feedback": "પ્રતિસાદ", "Login": "લૉગ ઇન", "Logout": "લૉગ આઉટ", "Get started": "શરૂ કરો", "Create account": "ખાતું બનાવો", "Welcome back": "ફરી સ્વાગત છે", "Overview": "ઝાંખી", "Preferences": "પસંદગીઓ", "Personal health": "વ્યક્તિગત આરોગ્ય", "Workspace": "વર્કસ્પેસ", "Admin": "એડમિન", "Patient profile": "દર્દી પ્રોફાઇલ", "Today's medicine reminders": "આજના દવાના રિમાઇન્ડર", "Upcoming appointments": "આગામી મુલાકાતો", "AI Health Assistant": "એઆઈ આરોગ્ય સહાયક", "Ask the assistant": "સહાયકને પૂછો", "View all": "બધું જુઓ", "Manage": "વ્યવસ્થા કરો", "Language": "ભાષા", "App language": "એપ ભાષા", "Display mode": "ડિસ્પ્લે મોડ", "Light": "લાઇટ", "Dark": "ડાર્ક", "Accent color": "મુખ્ય રંગ", "Interface color": "ઇન્ટરફેસ રંગ", "Health activity": "આરોગ્ય પ્રવૃત્તિ", "Delete account": "ખાતું કાઢી નાખો", "Close": "બંધ કરો", "Save": "સાચવો", "Save changes": "ફેરફારો સાચવો", "Edit profile": "પ્રોફાઇલ સંપાદિત કરો", "Search settings": "સેટિંગ્સ શોધો", "No matching settings found.": "મેળ ખાતી સેટિંગ્સ મળી નથી.", "Blood group": "બ્લડ ગ્રુપ", "Pending reminders": "બાકી રિમાઇન્ડર", "No medicine reminders for today.": "આજ માટે કોઈ દવાના રિમાઇન્ડર નથી.", "No upcoming appointments.": "કોઈ આગામી મુલાકાત નથી.", "Doctor": "ડૉક્ટર", "When": "ક્યારે", "Status": "સ્થિતિ", "Medicine": "દવા", "Time": "સમય", "General health information only, not a diagnosis.": "ફક્ત સામાન્ય આરોગ્ય માહિતી, નિદાન નથી.", "Chat": "ચેટ", "Recommendations": "ભલામણો", "Health summary": "આરોગ્ય સારાંશ", "Your question": "તમારો પ્રશ્ન", "Send": "મોકલો", "Voice": "અવાજ", "Speak response": "જવાબ સાંભળો", "Export PDF": "PDF નિકાસ કરો", "Quick prompts": "ઝડપી પ્રશ્નો", "Voice assistant": "અવાજ સહાયક", "Response ready.": "જવાબ તૈયાર છે.", "Are you sure?": "શું તમે ચોક્કસ છો?", "Date of birth": "જન્મ તારીખ", "Gender": "લિંગ", "Full name": "પૂરું નામ", "Username": "વપરાશકર્તા નામ", "Email": "ઇમેઇલ", "Phone": "ફોન", "Password": "પાસવર્ડ", "Confirm password": "પાસવર્ડની પુષ્ટિ કરો"
        }
    };
    var additions = {
        hi: {
            "Today's reminders": "आज के रिमाइंडर",
            "All reminders": "सभी रिमाइंडर",
            "View today's reminders": "आज के रिमाइंडर देखें",
            "Delete all reminders": "सभी रिमाइंडर हटाएं",
            "Mark completed": "पूर्ण चिह्नित करें",
            "No reminders in this group.": "इस समूह में कोई रिमाइंडर नहीं है।",
            "Stop voice": "आवाज़ रोकें",
            "Export Excel": "Excel निर्यात करें",
            "Export image": "चित्र निर्यात करें",
            "Ask a health-related question": "स्वास्थ्य संबंधी प्रश्न पूछें",
            "AI responses will appear here.": "AI के उत्तर यहां दिखाई देंगे।",
            "Thinking...": "सोच रहा है...",
            "Network error.": "नेटवर्क त्रुटि।",
            "The assistant could not complete this request.": "सहायक यह अनुरोध पूरा नहीं कर सका।",
            "The AI assistant is temporarily unavailable. Please try again later.": "AI सहायक अभी उपलब्ध नहीं है। कृपया बाद में पुनः प्रयास करें।",
            "Voice stopped.": "आवाज़ रोक दी गई।",
            "Voice captured. Sending...": "आवाज़ प्राप्त हुई। भेजा जा रहा है...",
            "Listening...": "सुन रहा है...",
            "Response ready.": "उत्तर तैयार है।",
            "Delete all ": "सभी ",
            " displayed reminders? This cannot be undone.": " दिखाए गए रिमाइंडर हटाएं? इसे पूर्ववत नहीं किया जा सकता।",
            "All reminders": "सभी रिमाइंडर",
            "Delete all displayed reminders? This cannot be undone.": "दिखाए गए सभी रिमाइंडर हटाएं? इसे पूर्ववत नहीं किया जा सकता।",
            "HealthMate AI Assistant": "HealthMate AI सहायक"
        },
        gu: {
            "Today's reminders": "આજના રિમાઇન્ડર",
            "All reminders": "બધા રિમાઇન્ડર",
            "View today's reminders": "આજના રિમાઇન્ડર જુઓ",
            "Delete all reminders": "બધા રિમાઇન્ડર કાઢી નાખો",
            "Mark completed": "પૂર્ણ તરીકે ચિહ્નિત કરો",
            "No reminders in this group.": "આ જૂથમાં કોઈ રિમાઇન્ડર નથી.",
            "Stop voice": "અવાજ બંધ કરો",
            "Export Excel": "Excel નિકાસ કરો",
            "Export image": "છબી નિકાસ કરો",
            "Ask a health-related question": "આરોગ્ય સંબંધિત પ્રશ્ન પૂછો",
            "AI responses will appear here.": "AI જવાબો અહીં દેખાશે.",
            "Thinking...": "વિચારી રહ્યું છે...",
            "Network error.": "નેટવર્ક ભૂલ.",
            "The assistant could not complete this request.": "સહાયક આ વિનંતી પૂર્ણ કરી શક્યું નથી.",
            "The AI assistant is temporarily unavailable. Please try again later.": "AI સહાયક હાલમાં ઉપલબ્ધ નથી. કૃપા કરીને પછીથી ફરી પ્રયાસ કરો.",
            "Voice stopped.": "અવાજ બંધ કરવામાં આવ્યો.",
            "Voice captured. Sending...": "અવાજ મળ્યો. મોકલી રહ્યા છીએ...",
            "Listening...": "સાંભળી રહ્યા છીએ...",
            "Response ready.": "જવાબ તૈયાર છે.",
            "Delete all ": "બધા ",
            " displayed reminders? This cannot be undone.": " બતાવેલા બધા રિમાઇન્ડર કાઢી નાખવા છે? આ પૂર્વવત્ કરી શકાશે નહીં.",
            "Delete all displayed reminders? This cannot be undone.": "બતાવેલા બધા રિમાઇન્ડર કાઢી નાખવા છે? આ પૂર્વવત્ કરી શકાશે નહીં.",
            "HealthMate AI Assistant": "HealthMate AI સહાયક"
        }
    };
    var dictionary = Object.assign({}, dictionaries[language] || {}, additions[language] || {});

    function translateValue(value) {
        if (!value) {
            return value;
        }
        if (dictionary[value]) {
            return dictionary[value];
        }
        var deletePrefix = "Delete all ";
        var deleteSuffix = " displayed reminders? This cannot be undone.";
        if (value.indexOf(deletePrefix) === 0 && value.indexOf(deleteSuffix) !== -1) {
            var count = value.slice(deletePrefix.length, value.indexOf(deleteSuffix));
            var translatedPrefix = dictionary[deletePrefix] || deletePrefix;
            return translatedPrefix + count + (dictionary[deleteSuffix] || deleteSuffix);
        }
        return value;
    }
    window.translateAppText = translateValue;

    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) {
        var original = node.nodeValue.trim();
        var translated = translateValue(original);
        if (translated !== original) {
            node.nodeValue = node.nodeValue.replace(original, translated);
        }
    }
    document.querySelectorAll("[placeholder], [title], [aria-label], [data-confirm]").forEach(function (element) {
        ["placeholder", "title", "aria-label", "data-confirm"].forEach(function (attribute) {
            var value = element.getAttribute(attribute);
            var translated = translateValue(value);
            if (translated !== value) {
                element.setAttribute(attribute, translated);
            }
        });
    });
    if (document.title) {
        document.title = translateValue(document.title);
    }
}

function initSidebarToggle() {
    var layout = document.getElementById("dashboardLayout");
    var closeBtn = document.getElementById("sidebarToggle");
    var openBtn = document.getElementById("sidebarReopen");
    var backdrop = document.getElementById("sidebarBackdrop");
    if (!layout || !closeBtn || !openBtn || !backdrop) {
        return;
    }
    function persist(open) {
        try {
            localStorage.setItem("aihealth.sidebar", open ? "open" : "closed");
        } catch (err) {
            /* ignore storage errors */
        }
    }
    function openMenu() {
        layout.classList.add("sidebar-open");
        openBtn.setAttribute("aria-expanded", "true");
        layout.setAttribute("data-sidebar-open", "true");
        persist(true);
    }
    function closeMenu() {
        layout.classList.remove("sidebar-open");
        openBtn.setAttribute("aria-expanded", "false");
        layout.setAttribute("data-sidebar-open", "false");
        persist(false);
    }
    closeBtn.addEventListener("click", function () {
        closeMenu();
    });
    openBtn.addEventListener("click", function () {
        openMenu();
    });
    backdrop.addEventListener("click", function () {
        closeMenu();
    });
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeMenu();
        }
    });
    var saved = "";
    try {
        saved = localStorage.getItem("aihealth.sidebar") || "";
    } catch (err) {
        saved = "";
    }
    var desktop = window.matchMedia && window.matchMedia("(min-width: 992px)").matches;
    if (saved === "open" || (!saved && desktop)) {
        layout.classList.add("sidebar-open");
        openBtn.setAttribute("aria-expanded", "true");
        layout.setAttribute("data-sidebar-open", "true");
    } else {
        layout.classList.remove("sidebar-open");
        openBtn.setAttribute("aria-expanded", "false");
        layout.setAttribute("data-sidebar-open", "false");
    }
}

function initSettingsSearch() {
    var input = document.getElementById("settingsSearch");
    if (!input) {
        return;
    }
    var sections = Array.prototype.slice.call(document.querySelectorAll("[data-settings-keywords]"));
    var empty = document.getElementById("settingsSearchEmpty");
    input.addEventListener("input", function () {
        var query = input.value.trim().toLowerCase();
        var visible = 0;
        sections.forEach(function (section) {
            var haystack = (section.getAttribute("data-settings-keywords") + " " + section.textContent).toLowerCase();
            var match = !query || haystack.indexOf(query) !== -1;
            section.classList.toggle("d-none", !match);
            if (match) {
                visible += 1;
            }
        });
        if (empty) {
            empty.classList.toggle("d-none", visible !== 0);
        }
    });
}

function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") || "" : "";
}

function escapeHtml(value) {
    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function initReminderNotifications() {
    var shownKey = "aihealth.shownReminders";
    var shown = {};
    try {
        shown = JSON.parse(sessionStorage.getItem(shownKey) || "{}") || {};
    } catch (err) {
        shown = {};
    }

    var modalEl = document.getElementById("reminderModal");
    if (!modalEl || typeof bootstrap === "undefined") {
        return;
    }
    var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    var queue = [];
    var current = null;
    var permissionAsked = false;
    var autoHideTimer = null;

    function persistShown() {
        sessionStorage.setItem(shownKey, JSON.stringify(shown));
    }

    function updateBadge(count) {
        var badge = document.getElementById("reminderBadge");
        if (!badge) {
            return;
        }
        if (count > 0) {
            badge.textContent = count > 9 ? "9+" : String(count);
            badge.classList.remove("d-none");
        } else {
            badge.classList.add("d-none");
        }
    }

    function markShown(id) {
        shown[id] = Date.now();
        persistShown();
    }

    function fillModal(item) {
        document.getElementById("reminderModalKicker").textContent = item.soon
            ? "Upcoming " + (item.type || "reminder").toLowerCase()
            : (item.type || "Reminder") + " now";
        document.getElementById("reminderModalTitle").textContent = item.title || "Reminder";
        document.getElementById("reminderModalDetail").textContent = item.detail || "";
        document.getElementById("reminderModalWhen").textContent = (item.date || "") + " at " + (item.time || "");
    }

    function showNext() {
        if (current || !queue.length) {
            return;
        }
        current = queue.shift();
        fillModal(current);
        modal.show();
        desktopNotify(current);
        window.clearTimeout(autoHideTimer);
        autoHideTimer = window.setTimeout(function () {
            if (current) {
                markShown(current.id);
                current = null;
                modal.hide();
            }
        }, 3000);
    }

    function desktopNotify(item) {
        if (!("Notification" in window) || Notification.permission !== "granted") {
            return;
        }
        try {
            new Notification(item.title || "Health reminder", {
                body: (item.detail || "") + " · " + (item.time || ""),
                tag: item.id
            });
        } catch (err) {
            /* ignore blocked notifications */
        }
    }

    function maybeAskPermission() {
        if (permissionAsked || !("Notification" in window) || Notification.permission !== "default") {
            return;
        }
        permissionAsked = true;
        Notification.requestPermission();
    }

    function showToast(item) {
        var host = document.getElementById("reminderToasts");
        if (!host) {
            return;
        }
        var el = document.createElement("div");
        el.className = "toast reminder-toast";
        el.setAttribute("role", "alert");
        el.innerHTML =
            '<div class="toast-header">' +
            '<strong class="me-auto">' + escapeHtml(item.title || "Reminder") + "</strong>" +
            '<small>' + escapeHtml(item.time || "") + "</small>" +
            '<button type="button" class="btn-close" data-bs-dismiss="toast"></button>' +
            "</div>" +
            '<div class="toast-body">' + escapeHtml(item.detail || "You have a reminder.") + "</div>";
        host.appendChild(el);
        bootstrap.Toast.getOrCreateInstance(el, { delay: 3000 }).show();
        el.addEventListener("hidden.bs.toast", function () {
            el.remove();
        });
    }

    modalEl.addEventListener("hidden.bs.modal", function () {
        window.clearTimeout(autoHideTimer);
        if (current) {
            markShown(current.id);
            current = null;
        }
        window.setTimeout(showNext, 250);
    });

    document.getElementById("reminderCompleteBtn").addEventListener("click", function () {
        if (!current) {
            return;
        }
        var item = current;
        fetch(item.complete_url, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken(),
                "X-Requested-With": "XMLHttpRequest",
                Accept: "application/json"
            },
            credentials: "same-origin"
        })
            .then(function (response) {
                return response.json().catch(function () {
                    return {};
                });
            })
            .then(function () {
                markShown(item.id);
                current = null;
                modal.hide();
            })
            .catch(function () {
                markShown(item.id);
                current = null;
                modal.hide();
            });
    });

    function poll() {
        fetch("/reminders/due", {
            credentials: "same-origin",
            headers: { Accept: "application/json" }
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("due fetch failed");
                }
                return response.json();
            })
            .then(function (data) {
                var items = (data && data.reminders) || [];
                updateBadge(items.length);
                items.forEach(function (item) {
                    if (shown[item.id]) {
                        return;
                    }
                    if (queue.some(function (queued) { return queued.id === item.id; }) || (current && current.id === item.id)) {
                        return;
                    }
                    queue.push(item);
                    showToast(item);
                    maybeAskPermission();
                });
                showNext();
            })
            .catch(function () {
                /* stay silent while offline */
            });
    }

    poll();
    window.setInterval(poll, 5000);
}
