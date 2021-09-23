Vue.component("modal", {
    template: `
        <div class="w3-modal">
            <div class="w3-modal-content">
                <header class="w3-container w3-theme">
                    <i class="w3-button w3-display-topright mdi mdi-close"
                       @click="$emit('close')"></i>
                    <slot name="header">Default Modal Header</slot>
                </header>
                
                <main class="w3-container">
                    <slot name="body">
                    <p>Default: Lorem ipsum etc. pp.</p>
                    </slot>
                </main>
                
                <footer class="w3-container w3-theme-light">
                    <slot name="footer">
                    <p>It's a default FOOTER!</p>
                    </slot>
                </footer>
            </div>
        </div>
    `
});

var app = new Vue({
    el: '#vue-app',
    delimiters: ["[[", "]]"], // set vuejs delimiters (because jinja2 uses {{ }})
    data: {
        data: {}, // transfer data from flask to vue.js
        modals: {help: false},
        checkWord: "",
        checkStatus: "",
    },
    methods: {
        deleteWord(id, word) {
            if(confirm("❓ Delete "+word+" from dictionary?")){
                fetch(
                    '/dictionary?action=delete', {
                    method: 'POST', // *GET, POST, PUT, DELETE, etc.
                    mode: 'cors',   // no-cors, *cors, same-origin
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                    },
                    credentials: 'same-origin', // include, *same-origin, omit
                    body: JSON.stringify({'id': id}), 
                }).then(response => {
                    return response.json();
                }).then(resJson => {
                    if (resJson.success == 'success') {
                        alert("✅ "+resJson.response);
                        location.reload();
                    } else {
                        alert("❗ "+resJson.response);
                    }
                });
            }
        },
        deletePrintersError(id, pattern) {
            if(confirm("❓ Delete "+pattern+" from list of printer's errors?")){
                fetch(
                    '/dictionary?action=deletePrintersError', {
                    method: 'POST', // *GET, POST, PUT, DELETE, etc.
                    mode: 'cors',   // no-cors, *cors, same-origin
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                    },
                    credentials: 'same-origin', // include, *same-origin, omit
                    body: JSON.stringify({'id': id}), 
                }).then(response => {
                    return response.json();
                }).then(resJson => {
                    if (resJson.success == 'success') {
                        alert("✅ "+resJson.response);
                        location.reload();
                    } else {
                        alert("❗ "+resJson.response);
                    }
                });
            }
        },
        deleteFromSymSpell() {
            var word = this.checkWord;
            if(confirm("❓ Delete "+word+" from the spellchecker's dictionary (SymSpell)?")){
                fetch(
                    '/dictionary?action=deleteFromSymSpell', {
                    method: 'POST', // *GET, POST, PUT, DELETE, etc.
                    mode: 'cors',   // no-cors, *cors, same-origin
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                    },
                    credentials: 'same-origin', // include, *same-origin, omit
                    body: JSON.stringify({'word': word}), 
                }).then(response => {
                    return response.json();
                }).then(resJson => {
                    if (resJson.success == 'success') {
                        alert("✅ "+resJson.response);
                        location.reload();
                    } else {
                        alert("❗ "+resJson.response);
                    }
                });
            }
        },
        reloadGoogleTables() {
            fetch(
                '/dictionary?action=reloadtables', {
                method: 'GET', // *GET, POST, PUT, DELETE, etc.
                mode: 'cors',   // no-cors, *cors, same-origin
                headers: {
                    'Accept': 'application/json',
                },
                credentials: 'same-origin', // include, *same-origin, omit
            }).then(response => {
                return response.json();
            }).then(resJson => {
                if (resJson.success == 'success') {
                    alert("✅ "+resJson.response);
                    location.reload();
                } else {
                    alert("❗ "+resJson.response);
                }
            });
        },
        importFromGoogle(source) {
            fetch(
                '/dictionary?action=importfromgoogle'
                + '&source=' + source, {
                method: 'GET', // *GET, POST, PUT, DELETE, etc.
                mode: 'cors',   // no-cors, *cors, same-origin
                headers: {
                    'Accept': 'application/json',
                },
                credentials: 'same-origin', // include, *same-origin, omit
            }).then(response => {
                return response.json();
            }).then(resJson => {
                if (resJson.success == 'success') {
                    alert("✅ "+resJson.response);
                    location.reload();
                } else {
                    alert("❗ "+resJson.response);
                }
            });
        },
        addCustomToDictionary(word, cts) {
            word = prompt("❓ Add a custom word to the dictionary:", word);
            if (word) { this.addToDictionary(word, cts); }
        },
        addToDictionary(word, cts) {
            this.message = "Updating dictionary ...";
            var word = word;
            word = word.replace("V", "U");
            word = word.replace("v", "u");
            word = word.replace("J", "I");
            word = word.replace("j", "i");
            fetch(
                '/dictionary?action=add'
                + '&word='+word 
                + '&cts='+cts, {
                method: 'POST', // *GET, POST, PUT, DELETE, etc.
                mode: 'cors',   // no-cors, *cors, same-origin
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin', // include, *same-origin, omit
                body: JSON.stringify({'word': word.toLowerCase(), 
                                      'cts': cts}), 
            }).then(response => {
                this.message = "";
                return response.json();
            }).then(resJson => {
                if (resJson.success == 'success') {
                    if(!alert("✅ "+resJson.response)) {
                    // Workaround because alert does not wait for the user to click OK!
                        location.reload();
                    }
                } else {
                    alert("❗ "+resJson.response);
                }
            });
        },
        addToPrintersErrors(pattern, cts) {
            pattern = prompt("❓ Treat this word as a printer's error?\n(You can add the replacement in the next step.)", pattern);
            if (pattern) {
                var replacement = prompt('❓ Replacement for "'+pattern+'":', pattern);
                if (replacement) {
            if (pattern == replacement) {
                alert("❗ The error and its replacement are identical. Therefore, they cannot be added to the list of printer's errors.");
                return false;
            }
            if (confirm("❓ Add the following pair to the list of printer's errors:\n"+pattern+" → "+replacement+" ?")) {
                this.message = "Updating printer's errors ...";
                fetch(
                    '/dictionary?action=addPrintersError'
                    + '&word='+pattern 
                    + '&cts='+cts, {
                    method: 'POST', // *GET, POST, PUT, DELETE, etc.
                    mode: 'cors',   // no-cors, *cors, same-origin
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                    },
                    credentials: 'same-origin', // include, *same-origin, omit
                    body: JSON.stringify({'pattern': pattern, 
                                          'replacement': replacement,
                                          'cts': cts}), 
                }).then(response => {
                    this.message = "";
                    return response.json();
                }).then(resJson => {
                    if (resJson.success == 'success') {
                        if (!alert("✅ "+resJson.response)) {
                            location.reload();
                        };
                    } else {
                        alert("❗ "+resJson.response);
                    }
                });
            }
                } else {
                    alert("❗ Cancelled");
                }
            } else {
                alert("❗ Cancelled");
            }
        },
    },
    mounted() {
        this.data = data; // transfer data from flask to vue.js
    },
    watch: {
        checkWord: function (val) {
            fetch(
                '/dictionary?action=check&word=' + this.checkWord, {
                method: 'GET', // *GET, POST, PUT, DELETE, etc.
                mode: 'cors',   // no-cors, *cors, same-origin
                headers: {
                    'Accept': 'application/json',
                },
                credentials: 'same-origin', // include, *same-origin, omit
            }).then(response => {
                return response.json();
            }).then(resJson => {
                if (resJson.success == 'success') {
                    this.checkStatus = "🟢 " + resJson.response;
                } else if (resJson.success == 'neutral') {
                    this.checkStatus = "";
                } else {
                    this.checkStatus = "🔴 " + resJson.response;
                }
            });
        },
    },

})

