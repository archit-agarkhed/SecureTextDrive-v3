from flask import Flask , session
import os
from flask_session import Session
# FrontENd

from views import views

from flask import *

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.register_blueprint(views, url_prefix="/")
app.secret_key = 'abcdlala'

# Use server-side session storage to avoid huge cookie (stores private keys)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(__file__), '.flask_session')
Session(app)



if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    app.run(debug=True, port=port)

