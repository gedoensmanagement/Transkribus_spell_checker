var app = new Vue({
    el: '#app',
    delimiters: ["[[", "]]"], // set vuejs delimiters (because jinja2 uses {{ }})
    data: {
        cols: {}, // transfer data from flask to vue.js
        selected_collections: [],
        selected_documents: [],
        selected_pages: [],
        exported_files: [],
        opened: 0,
        message: "",
        format: "tei_lera",
    },
    methods: {
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
        toggleDocs(docIdx) {
            if (this.opened != docIdx) {
                this.opened = docIdx;
                this.selected_pages = [];
                this.selected_documents = [];
            };
        },
        select_all(colIdx, docIdx, pages, event) {
            if (event.target.checked) {
                this.selected_pages = [];
                for (p of Object.keys(pages)) {
                    this.selected_pages.push(colIdx+"-"+docIdx+"-"+p);
                }
            } else {
                this.selected_pages = [];
            }
        },
        exportNow() {
            this.message = "exporting...";
            var pages = [];
            for (page of this.selected_pages) {
                page = page.split("-")[2];
                if (page != "all"){
                    pages.push(page);
                }
            }
            pages = pages.join();
            fetch(
                '/exporter?action=export'
                +'&colId='+this.selected_pages[0].split("-")[0]
                +'&docId='+this.selected_pages[0].split("-")[1]
                +'&format='+this.format
                +'&pages='+pages, {
                method: 'POST', // *GET, POST, PUT, DELETE, etc.
                mode: 'cors',   // no-cors, *cors, same-origin
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin', // include, *same-origin, omit
                body: JSON.stringify({'pages': pages}), 
            }).then(response => {
                this.message = "";
                return response.json();
            }).then(resJson => {
                if (resJson.success == "success") {
                    alert("✅ Exported successfully!\nYou can now download the file in the list below.");
                } else {
                    alert("❗ Error: "+resJson.response);
                }
                window.location.assign('/exporter'); // reload page to update list of downloadable files
            });
        },
        deleteFile(filename) {
            fetch('/exporter?action=delete&file='+filename, {
            method: 'DELETE',
            mode: 'cors',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin', // include, *same-origin, omit
            }).then(response => {
                return response.json();
            }).then(resJson => {
                if (resJson.success == "success") {
                    alert("✅ Deleted successfully!\n"+filename);
                } else {
                    alert("❗ Error: "+resJson.response);
                }
                window.location.assign('/exporter'); // reload page to update list of downloadable files
            });
        },
    },
    mounted() {
        this.cols = cols; // transfer data from flask to vue.js
        this.selected_pages = selected_pages;
        this.opened = opened;
        this.exported_files = exported_files;
    }
})

