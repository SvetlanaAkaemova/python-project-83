import bs4
import psycopg2
import psycopg2.extras
import os
import requests
import datetime
import validators
from flask import Flask, request, url_for, get_flashed_messages, flash, redirect, render_template
from dotenv import load_dotenv
from requests import ConnectionError, HTTPError
from urllib.parse import urlparse


app = Flask(__name__)


load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def get_content_of_page(url):
    get_page = requests.request('GET', url)
    page_content = get_page.text
    soup = bs4.BeautifulSoup(page_content, 'html.parser')
    content_dict = {'h1': '', 'title': '', 'content': ''}
    if soup.find('h1'):
        content_dict['h1'] = soup.find('h1').text.strip()
    if soup.find('title'):
        content_dict['title'] = soup.find('title').text.strip()
    if soup.find('meta', {"name": "description"}):
        content_dict['content'] = soup.find('meta', {"name": "description"}).attrs['content']
    return content_dict


@app.route('/')
def index():
    return render_template('index.html')


@app.post('/urls')
def post_url():
    url = request.form.get('url')
    if url == '':
        flash("Некорректный URL", "alert alert-danger")
        flash("URL обязателен", "alert alert-danger")
        return render_template(
            'index.html',
            url_input=url,
            messages=get_flashed_messages(with_categories=True)
        ), 422
    elif not validators.url(url):
        flash("Некорректный URL", "alert alert-danger")
        return render_template(
            'index.html',
            url_input=url,
            messages=get_flashed_messages(with_categories=True)
        ), 422
    url_for_norm = urlparse(url)
    norm_url = url_for_norm.scheme + '://' + url_for_norm.netloc
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor) as cur:
            cur.execute("""
                SELECT id FROM urls
                WHERE name = '{0}'""".format(norm_url))
            result = cur.fetchone()
    if result:
        flash("Страница уже существует", "alert alert-info")
        return redirect(url_for('url_added', id=result.id))

    with get_connection() as conn:
        with conn.cursor() as cur:
            date = datetime.date.today()
            cur.execute("""
                INSERT INTO urls (name, created_at)
                VALUES ('{0}', '{1}') RETURNING id""".format(norm_url, date))
            url_id = cur.fetchone()[0]
            conn.commit()
        flash("Страница успешно добавлена", "alert alert-success")
        return redirect(url_for('url_added', id=url_id))


@app.route('/urls/<id>')
def url_added(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            messages = get_flashed_messages(with_categories=True)
            cur.execute("""
                SELECT name, created_at
                FROM urls
                WHERE id = {0}""".format(id))
            url_name, url_created_at = cur.fetchone()

    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor) as cur:
            cur.execute("""
                SELECT id, created_at, status_code, h1, title, description
                FROM url_checks
                WHERE url_id = {0}
                ORDER BY id DESC""".format(id))
            rows = cur.fetchall()
    return render_template(
        'page.html',
        messages=messages,
        url_name=url_name,
        url_id=id,
        url_created_at=url_created_at.date(),
        check_list=rows
    )


@app.get('/urls')
def urls_get():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor) as cur:
            cur.execute("""
                SELECT
                DISTINCT ON (urls.id) urls.id, urls.name, MAX(url_checks.created_at), url_checks.status_code
                FROM urls
                LEFT JOIN url_checks ON urls.id = url_checks.url_id
                GROUP BY urls.id, url_checks.status_code
                ORDER BY urls.id DESC""")
            rows = cur.fetchall()
    return render_template(
        'pages.html',
        urls_list=rows
    )


@app.route('/urls/<id>/checks', methods=['POST'])
def id_check(id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor) as cur:
            cur.execute("""
                SELECT name
                FROM urls
                WHERE id = {0}""".format(id))
            result = cur.fetchone()

    url_name = result.name
    try:
        response = requests.get(url_name)
        response.raise_for_status()
    except (ConnectionError, HTTPError):
        flash("Произошла ошибка при проверке", "alert alert-danger")
        return redirect(url_for('url_added', id=id))

    status_code = response.status_code
    content_dict = get_content_of_page(url_name)
    with get_connection() as conn:
        with conn.cursor() as cur:
            date = datetime.date.today()
            cur.execute("""
                INSERT INTO url_checks (url_id, created_at, status_code, h1, title, description)
                VALUES ({0}, '{1}', {2}, '{3}', '{4}', '{5}')""".format(
                id, date, status_code, content_dict['h1'], content_dict['title'], content_dict['content']))
            conn.commit()
    flash("Страница успешно проверена", "alert alert-success")
    return redirect(url_for('url_added', id=id))
