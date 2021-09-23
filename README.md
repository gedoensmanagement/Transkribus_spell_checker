# Transkribus Spell Checker
This is a web app written in Python/Flask providing a spell checker for [Transkribus](https://transkribus.eu). The app is specialized on late-medieval Latin texts. It downloads the raw diplomatic transcription from Transkribus, normalizes it (resolves abbreviations, macrons, hyphenation, line breaks) and spell checks the text to detect possible transcription errors. 

In addition, the app can export the text in some special formats (for later usage with other specialized software like [TRACER](https://www.etrap.eu/research/tracer/)). It can also compare two texts on word/character level to detect censorship.

**This is work in progress written by a non-professional.**

## Set up the environment and install dependencies
* Create a new environment with Python 3.7 (!!) using [venv](https://docs.python-guide.org/dev/virtualenvs/) or [conda](https://docs.anaconda.com/), e.g. `conda create --name dh_blog python=3.7`.
* Activate the new environment, e.g. `conda activate dh_blog`.
* Clone this repository.
* Use `pip` to install the required Python packages: `pip install -r requirements.txt`.
* Download the Latin SymSpell dictionary (240 MB) from [here]() and copy it to `spellchecker_app/my_app/dictionaries/symspell_dictionary_LA.pickle` (Github has a strict file size limit of 100 MB).

## Initialize the Flask app
Before running the app the first time, you have to initialize the database:

* `flask db init` (initialize at first run)
* `db migrate`    (detect changes in `models.py`)
* `db upgrade`    (apply the changes)

This will create two new folders (`instance` and `migrations`) within your project folder.

## Run the Flask app
You to tell Flask the name of your app by setting an [environment variable](https://en.wikipedia.org/wiki/Environment_variable). You can also activate Flask's developer mode using an environment variable. There are different commands for that on every operating system.

Windows (Powershell):
* `$env:FLASK_APP='my_app`
* `$env:FLASK_ENV='development'`

Linux:
* `export FLASK_APP=my_app`
* `export FLASK_ENV=development`

Finally, we can start the Flask server:

* Use `cd` (Windows) or `ls` (Linux) to go to the project folder (i.e. the folder where `run.py` lives).
* Run Flask with `flask run`
* If everything works, you should see this line: `Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)` indicating the base URL of your development server.
* Visit either `127.0.0.1:5000/editor` or `127.0.0.1:5000/login` to get started (no `index.html` implemented yet).

