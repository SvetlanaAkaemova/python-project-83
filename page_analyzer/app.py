import os
from flask import Flask, render_template
from dotenv import load_dotenv


app = Flask(__name__)


load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


@app.route('/')
def hello_world():
    return render_template('index.html')
