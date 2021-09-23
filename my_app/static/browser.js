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

// Help https://stackoverflow.com/questions/48394303/pre-checking-checkbox-using-vuejs-and-v-model

new Vue({
    el: '#vue-app',
    delimiters: ["[[", "]]"], // prevent conflict with jinja2 which uses {{ }}
    data: {
        version: "", // data transfer from flask to vue.js
        cols: {}, // data transfer from flask to vue.js
        exportedFiles: {}, // data transfer from flask to vue.js
        downloadableFiles: {}, // data transfer from flask to vue.js
        comparableFiles: [], // data transfer from flask to vue.js
        comments: [],
        censorship: [],
        modals: {help: false, export: false, exporting: false, exportDone: false, delete: false},
        tables: {downloadableFiles: {reverse: false, sortKey: 'filename'}, 
            comments: {reverse: false, sortKey: 'cts'}, 
            censorship: {reverse: false, sortKey: 'cts'}},
        exportableStatus: ["FINAL", "GT"],
        tabFocus: "Browser",
        loading: [],
        exportFormat: "",
        separators: ".?!]:",
        id_addition: "",
        compareFormat: "html",
        filesToCompare: ["0"],
        selectedPages: [],
        selectedRange: "",
        openedCollection: 0,
        openedDocument: 0,
        openedDocumentTitle: "",
        sortKey: 'file',
    },
    methods: {
        async getDocuments(colIdx){
            console.log("fetching documents...");
            this.loading.push(colIdx);
            const base = '/cts/tr/'
            const query = `${colIdx}`
            const response = await fetch(base + query);
            const data = await response.json();
            this.cols[colIdx].docs = data.docs;
            
            this.loading = this.loading.filter(function(value, index, arr){ return value != colIdx; });
            console.log("done");
        },
        async getPages(colIdx, docIdx){
            console.log("fetching pages...");
            this.loading.push(`${colIdx}.${docIdx}`);
            const base = '/cts/tr/';
            const query = `${colIdx}/${docIdx}`;
            const response = await fetch(base + query);
            const data = await response.json();
            this.cols[colIdx].docs[docIdx].pages = data.pages;
            this.loading = this.loading.filter(function(value, index, arr){ return value != `${colIdx}.${docIdx}`; });
            console.log("done");
        },
        async getDownloadableFiles(){
            const base = '/download';
            const response = await fetch(base);
            const data = await response.json();
            this.downloadableFiles = data;
            //this.tableSortBy("downloadableFiles", this.tables.downloadableFiles.sortKey);
        },
        async getComments(){
            this.tabFocus = 'Comments';
            const base = '/comments';
            const response = await fetch(base);
            const data = await response.json();
            this.comments = data;
            //this.tableSortBy("comments", this.tables.comments.sortKey);
        },
        async getCensorship(){
            this.tabFocus = 'Censorship';
            const base = '/censorship';
            const response = await fetch(base);
            const data = await response.json();
            this.censorship = data;
            //this.tableSortBy("censorship", this.tables.censorship.sortKey);
        },
        getMetaData(cts){
            // Eats a string "colIdx" or "colIdx.docIdx".
            // If the collection does not contain documents, fetch the list of documents
            // If the document does not contain pages, fetch the list of pages
            junks = cts.split(".");
            if (Object.keys(this.cols[junks[0]].docs).length == 0){
                this.getDocuments(junks[0]);
            } else if ((typeof junks[1] != 'undefined') && (Object.keys(this.cols[junks[0]].docs[junks[1]].pages).length == 0)) {
                this.getPages(junks[0], junks[1]);
            }
        },
        openPageEditor(colIdx, docIdx, pageIdx){
            window.location.href = `/cts/tr/${colIdx}/${docIdx}/${pageIdx}/edit`;
        },
        pagestyle(status) {
            if (status == "NEW") {
                return {'background-color': '#fff2df'};
            } else if (status == "IN_PROGRESS") {
                return {'background-color': '#ffff00'};
            } else if (status == "DONE") {
                return {'background-color': '#66aaff'};
            } else if (status == "FINAL") {
                return {'background-color': '#66ffff'};
            } else if (status == "GT") {
                return {'background-color': '#66ff66'};
            } else {
                return {'background-color': 'grey'};
            }
        },
        clearSelection(docIdx){
            this.$refs['range'+docIdx][0].value = "";
            this.selectedPages = [];
            this.exportFormat = "";
        },
        exportDialog(colIdx, docIdx){
            this.openedCollection = colIdx;
            this.openedDocument = docIdx;
            this.openedDocumentTitle = this.exportedFiles[colIdx].docs[docIdx].title;
            this.modals.export = true;
        },
        async exportNow(){
            this.modals.exporting = true;
            const base = '/export';
            const pages = this.selectedPagesList.join(",");
            const query = `?colId=${this.openedCollection}&docId=${this.openedDocument}&format=${encodeURI(this.exportFormat)}&pages=${pages}&separators=${encodeURIComponent(this.separators)}&idAddition=${this.id_addition}`;
            const response = await fetch(base + query, {
                method: 'POST',
            });
            const data = await response.json();
            this.modals.exporting = false;
            this.modals.exportDone = data;
            this.getDownloadableFiles();
        },
        exportFinished(){
            this.modals.export = false; 
            this.modals.exportDone = false; 
            this.clearSelection(this.openedDocument);
            this.getDownloadableFiles();
        },
        tableSortBy(tableName, sortKey) {
            this.tables[tableName].reverse = (this.tables[tableName].sortKey == sortKey) ? ! this.tables[tableName].reverse : false;
            this.tables[tableName].sortKey = sortKey;
            this[tableName].sort((a,b) => {
                if (this.tables[tableName].reverse){
                    return a[sortKey].localeCompare(b[sortKey]);
                } else {
                    return b[sortKey].localeCompare(a[sortKey]);
                }
            });
        },
        async deleteNow(file){
            const base = '/download';
            const query = `?file=${file.filename}`;
            const response = await fetch(base + query, {
                method: 'DELETE',
            });
            const data = await response.json();
            this.getDownloadableFiles();
            this.modals.delete = false;
        },
        async compareNow(){
            this.loading.push("comparing");
            const base = '/compare';
            const payload = {'files': this.filesToCompare.slice(1), // list of files except the first one which is "0"
                             'format': this.compareFormat};
            const response = await fetch(base, {
                method: 'POST',
                headers: {
                    'Accept': 'text/html',
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });
            if (this.compareFormat == "html") {
                const html = await response.text();
                // Open a new window and display the html sent by the server:
                window.open("/compare").document.write(html);
            } else {
                const feedback = await response.json();
                alert(feedback.message);
            }
            this.loading = this.loading.filter(function(value, index, arr){ return value != "comparing"; });
            this.filesToCompare = ["0"];
            this.getDownloadableFiles();
        },
    },
    watch: {
        downloadableFiles: function(items){
            if (!Array.isArray(items)){
                const list = [];
                Object.keys(items).forEach(key => {
                    list.push(items[key]);
                });
                this.downloadableFiles = list;
            }
        },
        censorship: function(censorship){
            censorship.forEach(c => {
                if (!('timestamp' in c)) {
                    c.timestamp = new Date(parseInt(c.uuid.split("-")[1])).toISOString().split(".")[0];
                }
            })
        },
        selectedRange: function (val) {
            var pattern = new RegExp("^(\\s*\\d+\\s*\\-\\s*\\d+\\s*,?|\\s*\\d+\\s*,?)+$");
            if (pattern.test(this.selectedRange)) {
                this.selectedPages = [];
                const that = this;
                var parts = this.selectedRange.split(",");
                parts.forEach(function(part){
                    subparts = part.split("-");
                    if (subparts.length == 1){
                        if (subparts[0] != ""){
                            var a = parseInt(subparts[0]);
                            var pages = that.exportedFiles[that.openedCollection].docs[that.openedDocument].pages;
                            var max = Object.keys(pages).length;
                            if (a in pages){
                                if (that.exportableStatus.includes(pages[a].status)) {
                                    that.selectedPages.push(`${that.openedDocument}-${a.toString()}`);
                                }
                            }
                        }
                    } else {
                        var a = parseInt(subparts[0]);
                        var b = parseInt(subparts[1]);
                        var pages = that.exportedFiles[that.openedCollection].docs[that.openedDocument].pages;
                        var max = Object.keys(pages).length;
                        if ((a < b) && (a in pages) && (b in pages)) {
                            for (i = a; i < b + 1; i++) {
                                if (i in pages){
                                    if (that.exportableStatus.includes(pages[i].status)) {
                                        that.selectedPages.push(`${that.openedDocument}-${i.toString()}`); 
                                    }
                                }
                            }
                        }
                    }
                });
            }
        },
    },
    computed: {
        exportValidation: function(){
            if ((this.selectedPages != []) && (this.exportFormat != '')){
                return true;
            } else {
                return false;
            }
        },
        selectedPagesList: function(){
            const pagelist = [];
            this.selectedPages.forEach(page => {
                pagelist.push(page.split("-")[1]);
            });
            return pagelist;
        },
        compareFileFormat: function(){
            if ((this.compareFormat == "html") || (this.compareFormat == "raw_diff")){
                return "csv";
            } else if (this.compareFormat == "TRACER"){
                return "tsv";
            }
                
        },
    },
    mounted() {
        this.cols = cols; // data transfer from flask to vue.js
        this.exportedFiles = exportedFiles; // data transfer from flask to vue.js
        this.downloadableFiles = downloadableFiles; // data transfer from flask to vue.js
        this.formats = formats; // data transfer from flask to vue.js
        this.comparableFiles = comparableFiles; // data transfer from flask to vue.js
        this.version = version;
    }
});
