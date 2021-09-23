Vue.component("linenr", {
	props: ['lineNr', 'help', 'href'],
	template: `
		<span>
			<br />
			<span class="linenr" :title="help"><a :href="href" target="_blank">{{ lineNr }}</a></span> 
		</span>
	`
});

Vue.component("word", {
    props: ['classname', 'text', 'cts'],
    template: `
        <span :class="classname" :title="cts" :id="cts">{{ text }}</span>
    `
});

Vue.component("modal", {
    template: `
        <div class="w3-modal">
            <div class="w3-modal-content">
                <header class="w3-container w3-theme">
                    <!--<i class="w3-button w3-display-topright mdi mdi-close"
                       @click="$emit('close')"></i>-->
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

var app = new Vue ({
	el: '#vue-app',
	delimiters: ["[[", "]]"], // prevent conflict with jinja2 which uses {{ }}
	data: {
		texts: {'original': {},
				'censored': {}},
		files: [],
		user: 0,
        thisPage: 0,
        minPage: 0,
        maxPage: 0,
        censorshipBrowser: false,
        modals: {censorship: false, todo: false, help: false},
        errorMessage: false,
        checkHTML: "",
        checkData: [],
        censoredWords: [], // list of words that have been added or detracted
        censorships: [], // 
        registered: [], // contains cts if the word has already been registered as part of a censorship -> for highlighting
        todos: [],
	},
	methods: {
    	async get_data(file1, file2){
        	// Get data from server at start-up
            const base = '/compare';
            const payload = {'files': this.files, // list of files except the first one which is "0"
                             'format': 'raw_diff'};
            const response = await fetch(base, {
                method: 'POST',
                headers: {
                    'Accept': 'text/html',
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });
            this.texts = await response.json();
    		document.title = `${ this.texts.original.docTitle } vs. ${ this.texts.censored.docTitle }`;
            var pageRange = Object.keys(this.texts.pages);
            this.thisPage = pageRange[0];
            this.minPage = pageRange[0];
            this.maxPage = pageRange[pageRange.length - 1];
            
            // collect all words that have already been registered as part of a censorship:
            this.censoredWords.forEach(word => {
                if ((word.cts.split(".")[0] == this.texts.original.docTitle) || (word.cts.split(":")[0] == this.texts.censored.docTitle)) {
                    this.registered.push(word.cts);
                }
            });
    	},
        async get_censorship(cts){
            // Load censorship for a specific page from the server
            const base = `/censorship?cts=${cts}&source=${this.texts.censored.docTitle}`;
            const response = await fetch(base, {
                method: 'GET'});
            if (response.status == 200){
                var answer = await response.json();
                answer.forEach(c => {
                    if (this.censorships.filter(x => {return c.uuid == x.uuid}) == 0){
                        this.censorships.push(c);
                        this.get_censoredwords(c.uuid);
                    }
                });
            } else {
                console.log("No censorship in database for", cts);
            }
        },
        async get_censoredwords(uuid){
            const base = `/censorship/${uuid}`;
            const response = await fetch(base, {
                method: 'GET'});
            var answer = await response.json();
            if (response.status == 200) {
                answer.forEach(c => {
                    this.censoredWords.push(c);
                })
            }
        },
		cts(docTitle, ctsString){
			// eats a document title and a string like "78-r2l12"
			// returns a valid cts like zt:docTitle:pageNr.r0l0
			var cts = ctsString.split("-").join(".");
			return `zt:${docTitle}:${cts}`;
		},
        openCensorshipSidebar(){
            //console.log(this.$refs.censorshipSidebar);
            this.$refs.censorshipSidebar.style.display="block";
            this.$refs.censorshipSidebar.style.width="30%";
            this.$refs.edition.style.width="70%";
            this.$refs.censorshipSidebarButton.style.display="none";
        },
        closeCensorshipSidebar(){
            this.$refs.censorshipSidebar.style.display="none";
            this.$refs.edition.style.width="100%";
            this.$refs.censorshipSidebarButton.style.display="block";
        },
		doNewLine(pageIdx, lineIdx, wordIdx){
    		// Checks whether a new line begins or not:
			if (wordIdx == 0) {
                return true;
			} else if (this.texts.pages[pageIdx].words[wordIdx-1][2].split("@")[0] != lineIdx.split("@")[0]) {
                return true;
            } else {
				return false; 
			}
		},
        doNewCensoredPage(wordIdx){
            // Checks whether a new page begins:
            if (wordIdx == 0) {
                if (this.thisPage == this.minPage) {
                    return true;
                } else if (this.texts.pages[this.thisPage - 1].words[this.texts.pages[this.thisPage - 1].words.length - 1][4].split('.')[0] != this.texts.pages[this.thisPage].words[wordIdx][4].split('.')[0]) {
                    return true;
                //} else if (this.thisPage > this.maxPage) {
                //    return false;
                } else {
                    return false;
                }
            } else if (this.texts.pages[this.thisPage].words[wordIdx-1][4].split('.')[0] != this.texts.pages[this.thisPage].words[wordIdx][4].split('.')[0]) {
                return true;
            } else {
                return false;
            }
        },
        changePage(page) {
            this.thisPage = page;
        },
        registerDialog() {
            
            var thisNode = false;
            var lastNoe = false;
            
            // Make sure that we use only spans with relevant data, 
            // not empty text elements (NODE.textContent.replace(/(\n|\s)*/g, "") == "")
            // or linenumbers (NODE.lastChild != null)
            // document.getSelection().focusNode.textContent.replace(/(\n|\s)*/g, "")
            var anchor = document.getSelection().anchorNode;
            var focus = document.getSelection().focusNode;
            if (anchor.textContent.replace(/(\n|\s)*/g, "") == "" || anchor.lastChild != null) {
                thisNode = anchor.nextElementSibling;
            } else {
                thisNode = anchor.parentElement;
            }
            if (focus.textContent.replace(/(\n|\s)*/g, "") == "" || focus.lastChild != null) {
                lastNode = focus.previousElementSibling;
            } else {
                lastNode = focus.parentElement;
            }


            // Make sure we abort if the selection starts/ends on an added word or a line number:
            if ((thisNode.lastChild.className == "linenr") || (thisNode.className == "add") || (lastNode.lastChild.className == "linenr") || (lastNode.className == "add")) {
                this.errorMessage = '<i class="mdi mdi-alert"></i> Censorships cannot start/end on an added word or a line number. Please, modify your text selection.';
            } else {
                // OK, let's collect the words within the selection:
                var checkData = []
                var elements = []
                while (thisNode != lastNode) {
                    elements.push(thisNode);
                    thisNode = thisNode.nextElementSibling;
                }
                elements.push(lastNode);
                this.checkData = elements;
                
                // Save the html encoded selection: 
                var html = "";
                this.checkData.forEach(element => {
                    if (element.lastChild.className != "linenr") {
                        html += element.outerHTML.replace(/id=.*?\"/g, "") + " \n"; // deletes the "id" attribute
                    }
                });
                this.checkHTML = html;
            }
            this.modals['censorship'] = true;
        },
        registerAbort() {
            // Abort the registration of a new censorship:
            this.checkHTML = "";
            this.checkData = [];
            this.modals['censorship'] = false;
            this.errorMessage = false;
        },
        registerCensorship() {
            var uuid = `${this.user}-${Date.now()}`;
            var new_censoredWords = []
            var thisCts = ""
            
            // Add to the list of censored words:
            this.checkData.forEach((element, idx) => {
                
                this.registered.push(element.title); // brauch's das wirklich??
                
                if (idx == 0) {
                    thisCts = element.title;
                }
                
                // only added or detracted words are registered as censored words:
                var new_censoredWord = {};
                
                if (element.className == "det") {
                    new_censoredWord = {
                        cts: element.title,
                        type: element.className,
                        parent: uuid,
                        reference: "NULL",
                    };
                } else if (element.className == "") {
                    new_censoredWord = {
                        cts: element.title,
                        type: "NULL",
                        parent: uuid,
                        reference: "NULL",
                    };
                } else if (element.className == "add") {
                    var thisElement = element;
                    while (thisElement.title.split(":")[0] != this.texts.original.docTitle) {
                        thisElement = thisElement.previousElementSibling;
                    }
                    new_censoredWord = {
                        cts: element.title, // or thisElement to point to the word AFTER which the censorship has been added
                        type: element.className,
                        parent: uuid,
                        reference: element.title,
                    };
                }
                
                this.censoredWords.push(new_censoredWord);
                new_censoredWords.push(new_censoredWord);
            });
            
            var new_censorship = {
                cts: thisCts, // this.texts.original.docTitle + ":" + this.thisPage,
                source: this.texts.censored.docTitle,
                target: this.texts.original.docTitle,
                html: this.checkHTML,
                comment: this.$refs.CensorshipComment.value,
                uuid: uuid,
            };
            
            // Add to the list of censorships:
            this.censorships.push(new_censorship);
            
            // Close the modal and clean up:
            this.registerAbort();
            
            // Post the new censorship to the server:
            this.postCensorship(new_censorship, new_censoredWords);
        },
        async postCensorship(new_censorship, new_censoredWords){
            // Get data from server at start-up
            const base = '/censorship';
            const payload = {censorship: new_censorship,
                             censoredWords: new_censoredWords};
            const response = await fetch(base, {
                method: 'POST',
                headers: {
                    'Accept': 'text/html',
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });
            var answer = await response.json();
            if (response.status == 200) {
                alert(answer.message);
            } else {
                alert(`ERROR saving censorship! (Status: ${response.status})`);
            }
        },
        focusCensorship(uuid){
            for (let i=0; i<this.censoredWords.length; i++) {
                if (this.censoredWords[i].parent == uuid) {
                    var target = document.getElementById(this.censoredWords[i].cts);
                    var top = target.offsetTop - (window.innerHeight * 0.2);
                    window.scrollTo(0, top);
                    //console.log("Scroll to", top);
                    target.animate([{background: 'red', padding: '2px'}], 
                                    {duration: 500,
                                    iterations: 1,
                                    delay: 0});
                    break;
                }
            };
        },
        async deleteCensorship(uuid){
            if(confirm(`Do you really want to delete this censorship? (uuid: ${uuid})`)){
                this.censorships = this.censorships.filter(c => {return c.uuid != uuid});
                this.censoredWords = this.censoredWords.filter(w => {return w.parent != uuid});
                const base = `/censorship/${uuid}`
                const response = await fetch(base, {
                    method: 'DELETE'});
                var answer = await response.json();
                if (response.status == 200) {
                    alert(`Successfully deleted censorship (uuid: ${answer.uuid})`);
                } else {
                    alert(`ERROR: Couldn't delete censorship (uuid ${answer.uuid}, status: ${response.status})`);
                }
            }
        },
	},
    watch: {
        censoredWords: function(){
            // update the list of words for highlighting
            this.registered = [];
            this.censoredWords.forEach(word => {
                this.registered.push(word.cts);
            });
        },
        thisPage: function(){
            this.get_censorship(`${this.texts.original.docTitle}:${this.thisPage}`);
        },
    },
    mounted() {
        this.files = files;
        this.texts = texts;
        this.user = user;
		this.get_data(this.files[0], this.files[1]);
		
	},
    created(){
        var that = this;
        window.addEventListener('keyup', function(event) {
            if (event.keyCode == 82) {  // when "r" is pressed, open "register censorship" dialog
                if (that.modals.censorship != true && that.modals.todo != true) { // only if no modal opened
                    app.registerDialog();
                    app.$refs.CensorshipComment.focus();
                }
            }
        });
    },
});
