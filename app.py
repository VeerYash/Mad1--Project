from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.secret_key = 'Casper'
db = SQLAlchemy(app)

from routes import * 

if __name__ == '__main__':
    app.run(debug=True)