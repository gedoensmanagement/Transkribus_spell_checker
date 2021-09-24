SECRET_KEY=b'AN ACTUAL SECURE HEX KEY' 
# Cf. https://newbedev.com/where-do-i-get-a-secret-key-for-flask on how to
# generate a secure secret key!
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE='Lax'
PREFERRED_URL_SCHEME='https'

CORS_HEADERS='Content-Type'

SQLALCHEMY_DATABASE_URI = 'mysql://<YOUR SERVER>:<SOME STUFF>@localhost/<YOUR SERVER NAME>'

ABBREVIATIONS="https://docs.google.com/spreadsheets/d/e/2PACX-1vT-oEuvw0TTCyCl4bCBvhPXfACHx_tcGQO7nkA4_NOPKotRD6VRX2UDVQC4VyAFyy2zQwXs8A23eV24/pub?gid=0&single=true&output=csv"
PRINTERS_ERRORS="https://docs.google.com/spreadsheets/d/e/2PACX-1vT-oEuvw0TTCyCl4bCBvhPXfACHx_tcGQO7nkA4_NOPKotRD6VRX2UDVQC4VyAFyy2zQwXs8A23eV24/pub?gid=1286135488&single=true&output=csv"
DICTIONARY="https://docs.google.com/spreadsheets/d/e/2PACX-1vT-oEuvw0TTCyCl4bCBvhPXfACHx_tcGQO7nkA4_NOPKotRD6VRX2UDVQC4VyAFyy2zQwXs8A23eV24/pub?gid=738231180&single=true&output=csv"
