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
        modals: {help: false},
        page: {}, // transfer data from flask to vue.js
        comments: [], // transfer data from flask to vue.js
        keyboard: ["ā", "æ", "Æ", "ē", "ë", "ę", "ī", "ō", "œ", "ū", 
                   "ſ", "ʒ", 
                   "m̄", "n̄", "ń", 
                   "c̄", "đ",
                   "ꝓ", "ꝑ", "p̄",
                   "ꝙ", "ꝗ", "ꝗ̄", "ꝗ̃", "q́", "q̄", "q̊",
                   "⁹", "r̄", "ꝵ", "ꝶ", "t̄", "⁊"
                   ],
        keyboardActive: false,
        // status of the lines:
        active: {
                 regionIdx: false,
                 lineIdx: false,
                 ref: false,
                 oldValue: "",
                 },
        status: 0,
        // track changes and saving:
        message: "",
        saveState: "",

        // image of the page:
        pan: {x:0, y:300},
        size: {x:2300, y:3600},
        originalsize: {x:0, y:0},
        zoomSlider: 50,
        dragging: false,
        dragCursor: "grab",
        pointerPosition: {x:0, y:0},
        pointerOrigin: {x:0, y:0},
        fontSize: 14,
        imagePercentage: 30,
        // comment's visibility:
        commentsVisibility: false,
        activeComments: [],
    },
    methods: {
        // manage the page image:
        zoom()  {
            this.size.x = this.originalsize.x * (2 - this.zoomSlider/50);
            this.size.y = this.originalsize.y * (2 - this.zoomSlider/50);
        },
        getPointer() {
            this.point.x = event.clientX;
            this.point.y = event.clientY;
            const invertedSVGMatrix = this.$refs.svg.getScreenCTM().inverse()
            return this.point.matrixTransform(invertedSVGMatrix)
        },
        drag() {
            this.dragging = true;
            this.dragCursor = "grabbing";
            this.pointerOrigin = this.getPointer();
        },
        move() {
            if (this.dragging) {
                const pointerPosition = this.getPointer();
                this.pan.x -= (pointerPosition.x - this.pointerOrigin.x); 
                this.pan.y -= (pointerPosition.y - this.pointerOrigin.y);
            }
        },
        drop() {
            this.dragging = false;
            this.dragCursor = "grab";
        },
        // manage line editing:
        setFocus(regionIdx, lineIdx, coords) {
            this.active.regionIdx = regionIdx;
            this.active.lineIdx = lineIdx;
            this.active.ref = regionIdx + "-" + lineIdx;
            this.active.oldValue = this.$refs[this.active.ref][0].value;
            coords = coords.split(' ')[0].split(',');
            this.pan.x = coords[0]-15;
            this.pan.y = coords[1]-30;
        },
        unsetFocus() {
            this.active.regionIdx = false;
            this.active.lineIdx = false;
            this.active.ref = false;
        },
        gotoNextLine() {
            this.keyboardActive = false;
            if (event.shiftKey) {
                if (this.active.lineIdx - 1 >= 0) {
                    this.active.lineIdx--;
                    target = this.active.regionIdx+"-"+this.active.lineIdx;
                }
            } else {
                if (this.active.lineIdx + 1 < this.page.regions[this.active.regionIdx].lines.length) {
                    this.active.lineIdx++;
                    target = this.active.regionIdx+"-"+this.active.lineIdx;
                }
            }
            this.$refs[target][0].focus();
            this.$refs[target][0].setSelectionRange(0,0);
        },
        insert(char) {
            this.keyboardActive = true;
            if (this.active.ref != false) {
                input = this.$refs[this.active.ref][0];
                input.focus();
                // Workaround to prevent the cursor from 
                // jumping to the end and the inserted char from
                // being dropped:
                //oldValue = input.value;
                //input.value = "";
                //input.value = oldValue;
                // 
                // Oder den value des inputs vielleicht besser mit input.setRange() verändern??
                // https://javascript.info/selection-range#example-insert-at-cursor
                start = input.selectionStart;
                end = input.selectionEnd;
                cursorPos = start
                //scrollTop = input.scrollTop;
                input.value = input.value.substring(0, start)
                    + char
                    + input.value.substring(end, input.value.length);
                cursorPos += char.length;
                input.selectionStart = cursorPos;
                input.selectionEnd = cursorPos;
                //input.scrollTop = scrollTop;
                this.page.regions[this.active.regionIdx].lines[this.active.lineIdx].raw_data = input.value;
                //this.spellcheck();
            }
        },
        // https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch
        lineChanged() {
            if (this.keyboardActive == false && this.$refs[this.active.ref][0].value != this.active.oldValue) {
                this.saveState = "❗ unsaved changes ❗";
                //this.spellcheck();
            }
        },
        spellcheck() {
            this.message = "spellchecking...";
            fetch(window.location.pathname 
                + '?action=check'
                + "&colId="+this.page.colId
                + "&docId="+this.page.docId
                + "&pageNr="+this.page.pageNr, {
                method: 'POST', // *GET, POST, PUT, DELETE, etc.
                mode: 'cors',   // no-cors, *cors, same-origin
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin', // include, *same-origin, omit
                body: JSON.stringify(this.page),  // body must match Content-Type
            }).then(response => {
                return response.json();
            }).then(resJson => {
                this.page = resJson;
                this.prepareComments();
                this.message = "";
            });
        },
        // manage page I/O:
        save() {
            this.saveState = "Saving...";
            var saveState = this.saveState;
            fetch(window.location.pathname 
                + '?action=save'
                + "&colId="+this.page.colId
                + "&docId="+this.page.docId
                + "&pageNr="+this.page.pageNr, {
                method: 'POST', // *GET, POST, PUT, DELETE, etc.
                mode: 'cors',   // no-cors, *cors, same-origin
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin', // include, *same-origin, omit
                body: JSON.stringify(this.page),  // body must match Content-Type
            }).then(response => {
                this.saveState = "";
                return response.json();
            }).then(resJson => {
                if (resJson.success == 'success') {
                    alert("✅ Saved successfully!");
                } else {
                    alert("❗ Error while saving\n", resJson.response);
                }
            });
        },
        dump() {
            this.saveState = "Dumping...";
            fetch(window.location.pathname 
                + '?action=dump'
                + "&colId="+this.page.colId
                + "&docId="+this.page.docId
                + "&pageNr="+this.page.pageNr, {
                method: 'POST', // *GET, POST, PUT, DELETE, etc.
                mode: 'cors',   // no-cors, *cors, same-origin
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin', // include, *same-origin, omit
                body: JSON.stringify({'status': this.page.status}),  // body must match Content-Type
            }).then(response => {
                this.saveState = "";
                return response.json();
            }).then(resJson => {
                console.log(resJson.response);
                if (resJson.success == 'success') {
                    alert("✅ Saved successfully! "+resJson.response);
                } else {
                    alert("❗ "+resJson.response);
                }
            });
        },
        reload() { 
            if (this.saveState.includes("unsaved")) {
                if(confirm("❗ Unsaved changes will be lost!\n❓ Do you still want to reload this page?")){
                    this.message = "Reloading...";
                    window.location.assign(window.location.pathname 
                    + "?action=open"
                    + "&colId="+this.page.colId
                    + "&docId="+this.page.docId
                    + "&pageNr="+this.page.pageNr);
                }
            } else {
                this.message = "Reloading...";
                window.location.assign(window.location.pathname 
                + "?action=open"
                + "&colId="+this.page.colId
                + "&docId="+this.page.docId
                + "&pageNr="+this.page.pageNr);
            }
        },
        close() {
            if (this.saveState.includes("unsaved")) {
                if (confirm("❗ Unsaved changes will be lost!\n❓ Do you still want to close this page?")) {
                    window.location.assign(
                    window.location.pathname 
                    + "?action=close"
                    + "&colId="+this.page.colId
                    + "&docId="+this.page.docId
                    + "&pageNr="+this.page.pageNr);
                }
            } else {
                window.location.assign(
                window.location.pathname 
                + "?action=close"
                + "&colId="+this.page.colId
                + "&docId="+this.page.docId
                + "&pageNr="+this.page.pageNr);
            }
        },
        previousPage() {
            if (this.saveState.includes("unsaved")) {
                if (confirm("❗ Unsaved changes will be lost!\n❓ Do you still want to open page "+this.page.previous+"?")) {
                    this.message = "opening page "+ this.page.previous + "...";
                    window.location.assign(window.location.pathname 
                        + '?action=open'
                        + "&colId="+this.page.colId
                        + "&docId="+this.page.docId
                        + "&pageNr="+this.page.previous
                        + "&oldPageNr="+this.page.pageNr);
                }
            } else {
                this.message = "opening page "+ this.page.previous + "...";
                window.location.assign(window.location.pathname 
                    + '?action=open'
                    + "&colId="+this.page.colId
                    + "&docId="+this.page.docId
                    + "&pageNr="+this.page.previous
                    + "&oldPageNr="+this.page.pageNr);
            }
        },
        nextPage() {
            if (this.saveState.includes("unsaved")) {
                if (confirm("❗ Unsaved changes will be lost!\n❓ Do you still want to open page "+this.page.next+"?")) {
                    this.message = "opening page "+ this.page.next + "...";
                    window.location.assign(
                        window.location.pathname 
                        + '?action=open'
                        + "&colId="+this.page.colId
                        + "&docId="+this.page.docId
                        + "&pageNr="+this.page.next
                        + "&oldPageNr="+this.page.pageNr);
                } 
            } else {
                this.message = "opening page "+ this.page.next + "...";
                window.location.assign(
                    window.location.pathname 
                    + '?action=open'
                    + "&colId="+this.page.colId
                    + "&docId="+this.page.docId
                    + "&pageNr="+this.page.next
                    + "&oldPageNr="+this.page.pageNr);
            }
        },
        // Manage abbreviations, printer's errors, user dictionary
        reloadTables() {
            this.message = "Reloading tables ...";
            fetch(window.location.pathname 
                + '?action=reloadtables'
                + "&colId="+this.page.colId
                + "&docId="+this.page.docId
                + "&pageNr="+this.page.pageNr
            ).then(response => {
                this.message = "";
            });
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
                        //this.spellcheck();
                    }
                } else {
                    alert("❗ "+resJson.response);
                }
            });
        },
        addCustomToDictionary(word, cts) {
            word = prompt("❓ Add a custom word to the dictionary:", word);
            if (word) { this.addToDictionary(word, cts); }
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
                            this.spellcheck();
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
        editDictionary() {
            window.open('/dictionary?action=edit',
                'height=300,width=400');
        },
        toggleCommentsSidebar() {
            this.commentsVisibility = !this.commentsVisibility;
            if (this.commentsVisibility) {
                this.comments.forEach(function (comment) {
                    comment.highlighted = true;
                });
            }
        },
        addComment(regionIdx, lineIdx, wordIdx) {
            var oldState = this.commentsVisibility
            this.commentsVisibility = !oldState;
            comment = prompt("❓ Comment:", "");
            var cts = "tr:" + this.page.colId 
                + "."   + this.page.docId 
                + ":"   + this.page.pageNr
                + ".r"  + regionIdx
                + "l"   + lineIdx
                + "@"   + wordIdx;
            fetch(
                '/editor?action=addComment'
                + "&colId="+this.page.colId
                + "&docId="+this.page.docId
                + "&pageNr="+this.page.pageNr, {
                method: 'POST', // *GET, POST, PUT, DELETE, etc.
                mode: 'cors',   // no-cors, *cors, same-origin
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin', // include, *same-origin, omit
                body: JSON.stringify({'comment': comment, 
                                      'cts': cts}), 
            }).then(response => {
                return response.json();
            }).then(resJson => {
                this.comments = resJson.comments;
                this.prepareComments();
                if (resJson.success == 'success') {
                    alert("✅ "+resJson.response);
                } else {
                    alert("❗ "+resJson.response);
                }
            });
            this.commentsVisibility = oldState;
        },
        deleteComment(commentId, commentCts) {
            var oldState = this.commentsVisibility
            this.commentsVisibility = !oldState;
            fetch(
                '/editor?action=deleteComment'
                + "&colId="+this.page.colId
                + "&docId="+this.page.docId
                + "&pageNr="+this.page.pageNr, {
                method: 'POST', // *GET, POST, PUT, DELETE, etc.
                mode: 'cors',   // no-cors, *cors, same-origin
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin', // include, *same-origin, omit
                body: JSON.stringify({'commentId': commentId}), 
            }).then(response => {
                return response.json();
            }).then(resJson => {
                this.comments = resJson.comments;
                this.prepareComments(commentCts);
                if (resJson.success == 'success') {
                    alert("✅ "+resJson.response);
                } else {
                    alert("❗ "+resJson.response);
                }
            });
            this.commentsVisibility = oldState;
        },
        getWordFromCTS(cts) {
            // Help for decyphering the cts:
            // tr:47534.306609:3:r0l29@9
            // 0    1          2    3
            // OR
            // tr:47534.306609:3.r0l29@9
            // 0    1          2    3
            // var address = "r"+regionIdx+"l"+lineIdx+"@"+wordIdx
            var lastPart = cts.split(":")[2]
            if (lastPart.includes(".")) { // new format with dot: PAGE.rREGION
                lastPart = lastPart.split(".")[1];
            } else {                      // old format with colon: PAGE:rRegion
                lastPart = cts.split(":")[3];
            }

            var regionIdx = lastPart.split("@")[0].split("l")[0].slice(1);
            var lineIdx = lastPart.split("@")[0].split("l")[1];
            var wordIdx = lastPart.split("@")[1];
            word = this.page.regions[regionIdx].lines[lineIdx].words[wordIdx];

            return word;
        },
        gotoCTS(cts) {
            var lastPart = cts.split(":")[2]
            if (lastPart.includes(".")) { // new format with dot: PAGE.rREGION
                lastPart = lastPart.split(".")[1];
                console.log(lastPart);
            } else {                      // old format with colon: PAGE:rRegion
                lastPart = cts.split(":")[3];
            }
            var regionIdx = lastPart.split("@")[0].split("l")[0].slice(1);
            var lineIdx = lastPart.split("@")[0].split("l")[1];
            var element = this.$refs[regionIdx+"-"+lineIdx][0];
            var top = element.offsetTop - (window.innerHeight * this.imagePercentage / 100) - 10;
            window.scrollTo(0, top);
        },
        prepareComments(commentCts=false) {
            if (commentCts) {
                // Set the "hasComment" property of the corresponding word to "false".
                // If the word has other comments, "true" will be restored in the next
                // step. 
                this.getWordFromCTS(commentCts).hasComment = false;
            }
            var that = this;
            // For every comment set the "hasComment" property of the corresponding
            // word to "true":
            this.comments.forEach(function (comment) {
                comment.highlighted = true;
                that.getWordFromCTS(comment.cts).hasComment = true;
            });
        },
        showAllComments() {
            for (comment of this.comments) {
                this.commentsVisibility = false;
                comment.highlighted = true;
                this.commentsVisibility = true;
            }
        },
        toggleComment(word, regionIdx, lineIdx, wordIdx) {
            if (word.hasComment) {
                this.commentsVisibility = false;
                this.activeComments = [];
                var cts = 'r'+regionIdx+'l'+lineIdx+'@'+wordIdx;
                this.activeComments.push(cts);
                this.updateCommentHighlighting();
                this.commentsVisibility = true;
            }
        },
        updateCommentHighlighting() {
            for (comment of this.comments) {
                for (cts of this.activeComments) {
                    if (comment.cts.includes(cts)) {
                        comment.highlighted = true;
                    } else {
                        comment.highlighted = false;
                    }
                }
            }
        },
    },
//    created() {
//        window.addEventListener('beforeunload', (e) => {
//            e.preventDefault();
//            console.log("beforeunload");
//            window.location.assign(
//                window.location.pathname 
//                + "?action=close"
//                + "&colId="+this.page.colId
//                + "&docId="+this.page.docId);
//            e.returnValue = '';
//        });
//    },
    mounted() {
        this.page = page; // transfer data from flask to vue.js
        this.comments = comments; // transfer data from flask to vue.js
        this.prepareComments();

        this.size.x = this.page.imageWidth;
        this.size.y = this.page.imageHeight;
        // initialize SVGPoints for drag&drop panning
        this.pointerOrigin = this.$refs.svg.createSVGPoint();
        this.pointerPosition = this.$refs.svg.createSVGPoint();
        this.point = this.$refs.svg.createSVGPoint();

        this.originalsize = {x: this.size.x, 
                             y: this.$refs.svg.clientHeight};
        this.size = {x: this.originalsize.x,
                     y: this.originalsize.y}; 
        this.$refs.spinner.style.display = "none";
        document.title = this.page.title + " | p. " + this.page.pageNr;
    },
    watch: {
        saveState: function (val) {
            if (this.saveState.includes('ing')) {
                this.$refs.spinner.style.display = "inline-block";
            } else {
                this.$refs.spinner.style.display = "none";
            }
        },
        message: function (val) {
            if (this.message.includes('ing')) {
                this.$refs.spinner.style.display = "inline-block";
            } else {
                this.$refs.spinner.style.display = "none";
            }
        }
    },
    computed: {
        viewboxstring: function() {
            y = this.pan.y -30;
            return "" + this.pan.x +
                    " " + y + 
                    " " + this.size.x + 
                    " " + this.size.y;
        },
        highlightedComments: function() {
            return this.comments.filter(function (comment) {
                if (comment.highlighted) {
                    return comment;
                } 
            });
        },
    },
})
