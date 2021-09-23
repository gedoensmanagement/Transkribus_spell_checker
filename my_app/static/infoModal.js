Vue.component("modal", {
	template: `
			<div class="modal-content">
				<header>
					<span class="modal-close-btn"
						  @click="$emit('close')">&times;</span>
					<h2><slot name="header">Default Modal Header</slot></h2>
				</header>
				
				<div>
					<slot name="body">
					<p>Default: Lorem ipsum etc. pp.</p>
					</slot>
				</div>
				
				<div>
					<slot name="footer">
					<p>It's a default FOOTER!</p>
					</slot>
				</div>
			</div>
	`
});

var app = new Vue({
    el: '#app2',
    delimiters: ["[[", "]]"],
    data: {
        infoModal: false,
    }
});