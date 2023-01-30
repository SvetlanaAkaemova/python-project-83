import psycopg2
import os
import requests
import datetime
import validators
from flask import Flask, request, url_for, get_flashed_messages, flash, redirect, render_template
from dotenv import load_dotenv


app = Flask(__name__)


load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')


def get_id(db, dt, name):
    conn = psycopg2.connect(db)
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
def start():
    return render_template('start.html')


@app.post('/urls')
def post_url():
    url = request.form.get('url')
    if url == '':
        flash("Некорректный URL", "alert alert-danger")
        flash("URL обязателен", "alert alert-danger")
        return redirect(url_for('urls_get'))
    if not validators.url(url):
        flash("Некорректный URL", "alert alert-danger")
        return redirect(url_for('urls_get'))
    url_id_in_db = get_id(DATABASE_URL, 'urls', url)
    if url_id_in_db is None:
        conn = psycopg2.connect(DATABASE_URL)
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
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    messages = get_flashed_messages(with_categories=True)
    cur.execute("SELECT name, created_at FROM urls WHERE id = {0}".format(id))
    url_name, url_created_at = cur.fetchone()
    conn.close()
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, created_at, status_code FROM url_checks WHERE url_id = {0} ORDER BY id DESC".format(id)
    )
    rows = cur.fetchall()
    list_of_rows = list(map(list, rows))
    check_list = []
    for row in list_of_rows:
        check_list.append({'id': row[0], 'created_at': row[1].date(), 'status_code': row[2], 'h1': '', 'title': '', 'description': ''})
    conn.close()
    return render_template(
        'new_site.html',
        messages=messages,
        url_name=url_name,
        url_id=id,
        url_created_at=url_created_at.date(),
        check_list=check_list
    )


@app.get('/urls')
def urls_get():
    messages = get_flashed_messages(with_categories=True)
    if messages:
        return render_template(
            'start.html',
            messages=messages)
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT ON (urls.id) urls.id, urls.name, MAX(url_checks.created_at), url_checks.status_code FROM urls LEFT JOIN url_checks ON urls.id = url_checks.url_id GROUP BY urls.id, url_checks.status_code ORDER BY urls.id DESC"
    )
    rows = cur.fetchall()
    list_of_rows = list(map(list, rows))
    urls_list = []
    for row in list_of_rows:
        if row[3] is None:
            row[3] = ''
        if row[2] is None:
            row[2] = ''
        else:
            row[2] = row[2].date()
        urls_list.append({'id': row[0], 'name': row[1], 'check_data': row[2], 'response_code': row[3]})
    conn.close()
    return render_template(
        'site_list.html',
        urls_list=urls_list
    )


@app.route('/urls/<id>/checks', methods=['POST'])
def id_check(id):
    conn = psycopg2.connect(DATABASE_URL)
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
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    date = datetime.date.today()
    cur.execute(
        "INSERT INTO url_checks (url_id, created_at, status_code) VALUES ('{0}', '{1}', {2})".format(id, date, status_code)
    )
    conn.commit()
    conn.close()
    flash("Страница успешно проверена", "alert alert-success")
    return redirect(url_for('url_added', id=id))
