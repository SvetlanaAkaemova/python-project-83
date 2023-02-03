import bs4
import psycopg2
import os
import requests
import datetime
import validators
from flask import Flask, request, url_for, get_flashed_messages, flash, redirect, render_template
from dotenv import load_dotenv
from psycopg2 import OperationalError


app = Flask(__name__)


load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')


def create_connection(db):
    try:
        connection = psycopg2.connect(db)

    except OperationalError as e:
        print(f"The error '{e}' occured")
    return connection


def get_content_of_site(url):
    get_page = requests.request('GET', url)
    page_content = get_page.text
    soup = bs4.BeautifulSoup(page_content, 'html.parser')
    if soup.select('h1'):
        h1 = soup.select('h1')[0].text.strip()
    else:
        h1 = ''
    if soup.select('title'):
        title = soup.select('title')[0].text.strip()
    else:
        title = ''
    if soup.find('meta', {"name": "description"}):
        content = soup.find('meta', {"name": "description"}).attrs['content']
    else:
        content = ''
    return h1, title, content


def get_id(db, dt, name):
    conn = create_connection(db)
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM {0} WHERE name = '{1}'".format(dt, name)
    )
    result = cur.fetchall()
    id = [x[0] for x in result]
    conn.close()
    if id == []:
        return None
    return id[0]


@app.route('/')
def index():
    return render_template('index.html')


@app.post('/urls')
def post_url():
    url = request.form.get('url')
    messages = get_flashed_messages(with_categories=True)
    if url == '':
        flash("Некорректный URL", "alert alert-danger")
        flash("URL обязателен", "alert alert-danger")
        return render_template(
            'index.html',
            url_input=url,
            messages=messages
        )
    if not validators.url(url) and url != '':
        flash("Некорректный URL", "alert alert-danger")
        return render_template(
            'index.html',
            url_input=url,
            messages=messages
        )
    url_id_in_db = get_id(DATABASE_URL, 'urls', url)
    if url_id_in_db is None:
        conn = create_connection(DATABASE_URL)
        cur = conn.cursor()
        date = datetime.date.today()
        cur.execute(
            "INSERT INTO urls (name, created_at) VALUES ('{0}', '{1}')".format(url, date)
        )
        conn.commit()
        conn.close()
        url_id = get_id(DATABASE_URL, 'urls', url)
        flash("Страница успешно добавлена", "alert alert-success")
        return redirect(url_for('url_added', id=url_id))
    else:
        flash("Страница уже существует", "alert alert-info")
        return redirect(url_for('url_added', id=url_id_in_db))


@app.get('/urls/<id>')
def url_added(id):
    conn = create_connection(DATABASE_URL)
    cur = conn.cursor()
    messages = get_flashed_messages(with_categories=True)
    cur.execute(
        "SELECT name, created_at FROM urls WHERE id = {0}".format(id)
    )
    url_name, url_created_at = cur.fetchone()
    conn.close()
    conn = create_connection(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, created_at, status_code, h1, title, description FROM url_checks WHERE url_id = {0} ORDER BY id DESC".format(id)
    )
    rows = cur.fetchall()
    list_of_rows = list(map(list, rows))
    conn.close()
    check_list = []
    for row in list_of_rows:
        check_list.append({'id': row[0], 'created_at': row[1].date(), 'status_code': row[2], 'h1': row[3], 'title': row[4], 'description': row[5]})
    return render_template(
        'site.html',
        messages=messages,
        url_name=url_name,
        url_id=id,
        url_created_at=url_created_at.date(),
        check_list=check_list
    )


@app.get('/urls')
def urls_get():
    conn = create_connection(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT ON (urls.id) urls.id, urls.name, MAX(url_checks.created_at), url_checks.status_code FROM urls LEFT JOIN url_checks ON urls.id = url_checks.url_id GROUP BY urls.id, url_checks.status_code ORDER BY urls.id DESC"
    )
    rows = cur.fetchall()
    list_of_rows = list(map(list, rows))
    conn.close()
    urls_list = []
    for row in list_of_rows:
        if row[3] is None:
            row[3] = ''
        if row[2] is None:
            row[2] = ''
        else:
            row[2] = row[2].date()
        urls_list.append({'id': row[0], 'name': row[1], 'check_data': row[2], 'response_code': row[3]})
    return render_template(
        'sites.html',
        urls_list=urls_list
    )


@app.route('/urls/<id>/checks', methods=['POST'])
def id_check(id):
    conn = create_connection(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM urls WHERE id = {0}".format(id)
    )
    result = cur.fetchall()
    conn.close()

    url_name = [x[0] for x in result][0]
    response = requests.get(url_name)
    status_code = response.status_code
    if status_code != 200:
        flash("Произошла ошибка при проверке", "alert alert-danger")
        return redirect(url_for('url_added', id=id))
    h1, title, content = get_content_of_site(url_name)
    conn = create_connection(DATABASE_URL)
    cur = conn.cursor()
    date = datetime.date.today()
    cur.execute(
        "INSERT INTO url_checks (url_id, created_at, status_code, h1, title, description) VALUES ('{0}', '{1}', {2}, '{3}', '{4}', '{5}')".format(id, date, status_code, h1, title, content)
    )
    conn.commit()
    conn.close()
    flash("Страница успешно проверена", "alert alert-success")
    return redirect(url_for('url_added', id=id))
