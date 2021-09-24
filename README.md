# Transkribus Spell Checker
This is a web app written in Python/Flask providing a spell checker for [Transkribus](https://transkribus.eu). The app is specialized on late-medieval Latin texts. It downloads the raw diplomatic transcription from Transkribus, normalizes it (resolves abbreviations, macrons, hyphenation, line breaks) and spell checks the text to detect possible transcription errors. 

In addition, the app can export the text in some special formats (for later usage with other specialized software like [TRACER](https://www.etrap.eu/research/tracer/)). It can also compare two texts on word/character level to detect censorship.

**This is work in progress written by a non-professional.**

## Set up the environment and install dependencies
* Create a new environment with Python 3.7 (!!) using [venv](https://docs.python-guide.org/dev/virtualenvs/) or [conda](https://docs.anaconda.com/), e.g. `conda create --name dh_blog python=3.7`.
* Activate the new environment, e.g. `conda activate dh_blog`.
* Clone this repository.
* Use `pip` to install the required Python packages: `pip install -r requirements.txt`.
* Download the Latin SymSpell dictionary (240 MB) from [here]() and copy it to `my_app/dictionaries/symspell_dictionary_LA.pickle` (Github has a strict file size limit of 100 MB).

## Before running Flask
You have to tell Flask the name of your app by setting an [environment variable](https://en.wikipedia.org/wiki/Environment_variable). You can also activate Flask's developer mode using an environment variable. There are different commands for that on every operating system.

Windows (Powershell):
* `$env:FLASK_APP='my_app'`
* `$env:FLASK_ENV='development'`

Linux:
* `export FLASK_APP=my_app`
* `export FLASK_ENV=development`

## Initialize the Flask app
Before running the app the first time, you have to initialize the database:

* Set environment variables: 
  * `FLASK_APP` = `my_app`
  * `FLASK_ENV` = `development`
  * `INIT_DB` = `True` (This prevents errors when you initialize the database for the first time.)
* `flask db init` (initialize at first run)
* `flask db migrate`    (detect changes in `models.py`)
* `flask db upgrade`    (apply the changes)
* Don't forget to set `INIT_DB` to something else than `True` before starting the Flask app regularly! `$env:INIT_DB='False'` (Windows, Powershell) or `export INIT_DB=False` (Linux)

This will create two new folders (`instance` and `migrations`) within your project folder.

* Check out the instance folder: `test-config.py` defines variables for running the Flask app locally in development mode (see below), `config.py` does the same for running the app in production (i.e. on a 'real' server out in the internet). Make sure to modify these veriables according to your needs!

## Running the Flask app

Finally, we can start the Flask server:

* Use `cd` (Windows) or `ls` (Linux) to go to the project folder (i.e. the folder where `run.py` lives).
* Make sure to set the `FLASK_APP` environment variable to `my_app` (see above).
* Run Flask with `flask run`.
* If everything works, you should see some status messages. Loading the SymSpell dictionary takes some time! Somewhere you should see this line: `Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)` indicating the base URL of your development server.
* Visit e`127.0.0.1:5000/login` to get started (no `index.html` implemented yet).

## Using the app
### Register yourself as a user
* Before you can use the app, you have to register yourself with your Transkribus username and password. Other credentials won't work because the registration function checks whether your credentials are valid on the Transkribus server. 
* After your registration, you should be able to log in. 
### Opening a page in the editor
* The page you want to open must have at least one TextRegion that is tagged as "paragraph" (see this [tutorial on how to use structural tagging in Transkribus](https://readcoop.eu/transkribus/howto/how-to-use-the-structural-tagging-feature-and-how-to-train-it/)). ALL TextRegions must be tagged with a structure type! The "paragraph" TextRegions need to have BaseLines an the lines must contain text. If one of this conditions fails, the editor will show an error.
### Always log out and always close the pages with the "x" button
* When you leave the editor, make sure to close pages with the bottom right "x" button, otherwise the page stays locked for other users. (This is only relevant if you work in a team and run the app on a server on the internet.)
* Make sure to log out: This clears the in-memory cache and deletes all your page locks. 
### Stop the server
* Having logged out, you should stop the server on the command line by pressing `Ctrl-c`. Sometimes, you have to press it twice.
