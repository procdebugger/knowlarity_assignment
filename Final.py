import time
from sqlite3 import dbapi2 as sqlite3
from hashlib import md5
from datetime import datetime
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash, _app_ctx_stack
from werkzeug import check_password_hash, generate_password_hash


# configuration
DATABASE = 'contacts.db'
PER_PAGE = 30
DEBUG = True
SECRET_KEY = 'development key'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('MINITWIT_SETTINGS', silent=True)


def get_db():
    top = _app_ctx_stack.top
    if not hasattr(top, 'sqlite_db'):
        top.sqlite_db = sqlite3.connect(app.config['DATABASE'])
        top.sqlite_db.row_factory = sqlite3.Row
    return top.sqlite_db


@app.teardown_appcontext
def close_database(exception):
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()


def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    init_db()
    print('Initialized the database.')


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv


def get_user_id(username):
    rv = query_db('select user_id from user where username = ?',
                  [username], one=True)
    return rv[0] if rv else None


def format_datetime(timestamp):
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d @ %H:%M')


def gravatar_url(email, size=80):
    return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = query_db('select * from user where user_id = ?',
                          [session['user_id']], one=True)


@app.route('/')
def index():
    if not g.user:
        return redirect(url_for('login'))
    if 'user_id' not in session:
        abort(401)
    
    contacts=query_db('select contact_id, contact_name, email, address, phone_no from contact where user_id = ? order by contact_name',[session['user_id']])	
    if contacts is None:
       error = 'No Contacts'
       flash('No Contacts')
       return render_template('index.html')
    else:
       return render_template('index.html', contacts=contacts)
       
@app.route('/search_contact', methods=['POST'])
def search_contact():
    contacts = None
    if 'user_id' not in session:
        abort(401)
        error = None
	
    if request.form['text'] == '':	
	    return redirect(url_for('index'))	
	
    if request.form['text'] != '':
       contacts = query_db('select contact_id, contact_name, email, address, phone_no from contact where contact_name = ?', [ request.form['text']])
       #flash(contacts['contact_name'])
       if contacts is None:
          return redirect(url_for('index'))
       else:	   
          return render_template('index.html', contacts=contacts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        user = query_db('''select * from user where
            username = ?''', [request.form['username']], one=True)
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['pw_hash'],
                                     request.form['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['user_id'] = user['user_id']
            return redirect(url_for('index'))
    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif not request.form['email'] or \
                '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two passwords do not match'
        elif get_user_id(request.form['username']) is not None:
            error = 'The username is already taken'
        else:
            db = get_db()
            db.execute('''insert into user (
              username, email, pw_hash) values (?, ?, ?)''',
              [request.form['username'], request.form['email'],
               generate_password_hash(request.form['password'])])
            db.commit()
            flash('You were successfully registered and can login now')
            return redirect(url_for('login'))
    return render_template('register.html', error=error)

@app.route('/contacts', methods=['GET', 'POST'])
def contacts():
    #if g.user:
    #   return redirect(url_for('login'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a name'
        elif not request.form['email'] or \
                '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['address']:
            error = 'You have to enter a address'
        else:
            db = get_db()
            db.execute('''insert into contact (
              contact_name, email, address, phone_no, user_id) values (?, ?, ?, ?, ?)''',
              [request.form['username'],
               request.form['email'], request.form['address'], request.form['phone_no'], session['user_id']])
            db.commit()
            flash('You were successfully added a new contact')
            return redirect(url_for('index'))
    return render_template('contacts.html', error=error)	

@app.route('/update_contacts', methods=['GET', 'POST'])
def update_contacts():
    if g.user:
        selectedContact = None
        contacts=query_db('select contact_name, email, address, phone_no from contact where user_id = ? order by contact_name desc',[session['user_id']])
        if not contacts:
            flash("There is no Contacts to Update")
            return redirect(url_for('index'))
        return render_template('update_contacts.html', contacts=contacts ,selectedContact=selectedContact)
    error = None	

@app.route('/select_contact', methods=['GET', 'POST'])
def select_contact():
    if g.user:
       selectedContact = None
       contacts = None
       if request.method == 'POST':
        flash(request.form['contact'])
        selectedContact=query_db('select contact_id, contact_name, email, address, phone_no from contact where contact_name=? and user_id = ?',[ request.form['contact'],session['user_id']], one=True)
        if not selectedContact:
            flash("There is no Contacts to Update")
            return redirect(url_for('index'))
        contacts=query_db('select contact_name, email, address, phone_no from contact where user_id = ? order by contact_name desc',[session['user_id']])
       if not contacts:
            flash("There is no Contacts to Update")
            return redirect(url_for('index'))
       return render_template('update_contacts.html',selectedContact=selectedContact,contacts=contacts)
	
@app.route('/update' , methods=['GET', 'POST'])
def update():
    error = None
    if request.method == 'POST':
            db = get_db()
            db.execute('''update contact set contact_name = ?, email = ?, address  = ?, phone_no = ? where contact_id = ?''',
              [request.form['contact_name'],request.form['email'],request.form['address'], request.form['phone_no'], request.form['contact_id']])
            db.commit()
            flash('You were successfully Modified a existing contact')
            return redirect(url_for('index'))
    return render_template('update_contacts.html', error=error)		

@app.route('/delete_contacts', methods=['GET', 'POST'])
def delete_contacts():
    if g.user:
        contacts=query_db('select contact_name from contact where user_id = ? order by contact_name desc',[session['user_id']])
       
    if not contacts:
          flash("There is no Contacts to Delete")
          return redirect(url_for('index'))
    else:
          return render_template('delete_contacts.html', contacts=contacts)
    error = None

@app.route('/delete' , methods=['GET', 'POST'])
def delete():
    error = None
    if request.method == 'POST':
            db = get_db()
            db.execute('delete from contact where contact_name = ?',
              [request.form['contact']])
            db.commit()
            flash(request.form['contact'], 'You were successfully Deleted a existing contact')
            return redirect(url_for('index'))
    return render_template('delete_contacts.html', error=error)	
	
@app.route('/logout')
def logout():
    flash('You were logged out')
    session.pop('user_id', None)
    return redirect(url_for('login'))


# add some filters to jinja
app.jinja_env.filters['datetimeformat'] = format_datetime
app.jinja_env.filters['gravatar'] = gravatar_url
