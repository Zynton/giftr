"""Serve the app's views on a webserver."""

# For webserver
from BaseHTTPServer import (BaseHTTPRequestHandler,
                           HTTPServer)
import cgi  # Common Gateway Interface

# For CRUD
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import (Base,
                    User,
                    Gift,
                    Claim,
                    Category)

from flask import (Flask,
                   request,
                   redirect,
                   url_for,
                   render_template,
                   flash,
                   jsonify,
                   g,
                   session,
                   make_response)

# For OAuth
from google.oauth2 import id_token
from google.auth.transport import requests as g_requests
from oauth2client.client import (flow_from_clientsecrets,
                                 FlowExchangeError)
import random, string, httplib2, json, requests

# Bind database
engine = create_engine('sqlite:///giftr.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
c = DBSession()

# Bind Flask
app = Flask(__name__)

# API Secrets and IDs
# Get client id for Google OAuth2, from json file
google_client_secrets_f = open('google_client_secrets.json', 'r')
google_client_secrets = google_client_secrets_f.read()
google_client_secrets_json = json.loads(google_client_secrets)
CLIENT_ID = google_client_secrets_json['web']['client_id']


# ROUTES
# Client routes
# Gifts
@app.route('/', methods=['GET'])
@app.route('/gifts', methods=['GET'])
def get_gifts():
    categories = c.query(Category).all()

    req_cat = request.args.get('cat')
    try:
        req_cat = int(req_cat)
        if req_cat > 0 and req_cat <= len(categories):
            gifts = c.query(Gift).filter_by(category_id=req_cat).order_by(Gift.created_at.desc()).all()
            req_cat = c.query(Category).filter_by(id=req_cat).first()

            return render_template('gifts.html',
                                   gifts=gifts,
                                   categories=categories,
                                   req_cat=req_cat)
    except:
        pass
    
    gifts = c.query(Gift).order_by(Gift.created_at.desc()).all()

    return render_template('gifts.html',
                           categories=categories,
                           gifts=gifts)


@app.route('/gifts/add', methods=['GET'])
def show_add_gift():
    categories = c.query(Category).all()
    
    return render_template('add_gift.html',
                           categories=categories)

@app.route('/gifts/add', methods=['POST'])
def add_gift():
    gift = Gift(name=request.form.get('name'),
                picture=request.form.get('picture'),
                description=request.form.get('description'),
                category_id=request.form.get('category'))
    c.add(gift)
    c.commit()

    return redirect(url_for('get_gift_byid',
                            g_id=gift.id))


@app.route('/gifts/<int:g_id>', methods=['GET'])
def get_gift_byid(g_id):
    gift = c.query(Gift).filter_by(id=g_id).first()
    categories = c.query(Category).all()

    return render_template('gift.html',
                           gift=gift,
                           categories=categories)


@app.route('/gifts/<int:g_id>/edit', methods=['GET'])
def show_edit_gift(g_id):
    gift = c.query(Gift).filter_by(id=g_id).first()
    categories = c.query(Category).all()

    return render_template('edit_gift.html',
                           gift=gift,
                           categories=categories)

    
@app.route('/gifts/<int:g_id>/edit', methods=['POST'])
def edit_gift(g_id):
    gift = c.query(Gift).filter_by(id=g_id).first()

    gift.name = request.form.get('name')
    gift.picture = request.form.get('picture')
    gift.description = request.form.get('description')
    gift.category_id = request.form.get('category')

    c.add(gift)
    c.commit()

    return redirect(url_for('get_gift_byid',
                            g_id=gift.id))


@app.route('/gifts/<int:g_id>/delete', methods=['GET'])
def show_delete_gift(g_id):
    gift = c.query(Gift).filter_by(id=g_id).first()

    return render_template('delete_gift.html',
                           gift=gift)


@app.route('/gifts/<int:g_id>/delete', methods=['POST'])
def delete_gift(g_id):
    gift = c.query(Gift).filter_by(id=g_id).first()

    c.delete(gift)
    c.commit()

    # Delete the claims to that object too
    claims = c.query(Claim).filter_by(gift_id=gift.id).all()
    for claim in claims:
        c.delete(claim)
        c.commit()

    return redirect(url_for('get_gifts'))


# Claims
@app.route('/gifts/claims', methods=['GET'])
def get_all_claims():
    claims = c.query(Claim).all()

    return render_template('claims.html',
                           claims=claims)


@app.route('/gifts/<int:g_id>/claims', methods=['GET'])
def get_claims(g_id):
    claims = c.query(Claim).filter_by(gift_id=g_id).all()
    gift = c.query(Gift).filter_by(id=g_id).first()

    return render_template('claims.html',
                           gift=gift,
                           claims=claims)


@app.route('/gifts/<int:g_id>/claims/add', methods=['GET'])
def show_add_claim(g_id):
    gift = c.query(Gift).filter_by(id=g_id).first()

    return render_template('add_claim.html',
                           gift=gift)


@app.route('/gifts/<int:g_id>/claims', methods=['POST'])
def add_claim(g_id):
    claim = Claim(message=request.form.get('message'),
                  gift_id=g_id)

    c.add(claim)
    c.commit()

    return redirect(url_for('get_claim_byid',
                            g_id=g_id,
                            c_id=claim.id))


@app.route('/gifts/<int:g_id>/claims/<int:c_id>', methods=['GET'])
def get_claim_byid(g_id, c_id):
    claim = c.query(Claim).filter_by(id=c_id).first()

    return render_template('claim.html',
                           claim=claim)


@app.route('/gifts/<int:g_id>/claims/<int:c_id>/edit', methods=['GET'])
def show_edit_claim(g_id, c_id):
    claim = c.query(Claim).filter_by(id=c_id).first()

    return render_template('edit_claim.html',
                           claim=claim)


@app.route('/gifts/<int:g_id>/claims/<int:c_id>/edit', methods=['POST'])
def edit_claim(g_id, c_id):
    claim = c.query(Claim).filter_by(id=c_id).first()

    claim.message = request.form.get('message')

    c.add(claim)
    c.commit()

    return redirect(url_for('get_claim_byid',
                            g_id=g_id,
                            c_id=c_id))


@app.route('/gifts/<int:g_id>/claims/<int:c_id>/delete', methods=['GET'])
def show_delete_claim(g_id, c_id):
    claim = c.query(Claim).filter_by(id=c_id).first()

    return render_template('delete_claim.html',
                           claim=claim)


@app.route('/gifts/<int:g_id>/claims/<int:c_id>/delete', methods=['POST'])
def delete_claim(g_id, c_id):
    claim = c.query(Claim).filter_by(id=c_id).first()

    c.delete(claim)
    c.commit()

    return redirect(url_for('get_claims',
                            g_id=g_id))


# Users
@app.route('/users', methods=['GET', 'POST'])
def cr_users():
    return 'GET or POST users'


@app.route('/users/<int:u_id>', methods=['GET', 'UPDATE', 'DELETE'])
def rud_users(u_id):
    return 'GET, UPDATE or DELETE user %s' % u_id


# Categories
@app.route('/categories', methods=['GET'])
def get_categories():
    categories = c.query(Category).all()

    return render_template('categories.html',
                           categories=categories)


@app.route('/categories/add', methods=['GET'])
def show_add_category():
    return render_template('add_category.html')


@app.route('/categories', methods=['POST'])
def add_category():
    category = Category(name=request.form.get('name'),
                        picture=request.form.get('picture'),
                        description=request.form.get('description'))

    c.add(category)
    c.commit()

    return redirect(url_for('get_category_byid',
                            cat_id=category.id))


@app.route('/categories/<int:cat_id>', methods=['GET'])
def get_category_byid(cat_id):
    category = c.query(Category).filter_by(id=cat_id).first()

    return render_template('category.html',
                           category=category)


@app.route('/categories/<int:cat_id>/edit', methods=['GET'])
def show_edit_category(cat_id):
    category = c.query(Category).filter_by(id=cat_id).first()

    return render_template('edit_category.html',
                           category=category)


@app.route('/categories/<int:cat_id>', methods=['POST'])
def edit_category(cat_id):
    category = c.query(Category).filter_by(id=cat_id).first()

    category.name = request.form.get('name')
    category.picture = request.form.get('picture')
    category.description = request.form.get('description')

    c.add(category)
    c.commit()

    return redirect(url_for('get_category_byid',
                            cat_id=category.id))


@app.route('/categories/<int:cat_id>/delete', methods=['GET'])
def show_delete_category(cat_id):
    category = c.query(Category).filter_by(id=cat_id).first()

    return render_template('delete_category.html',
                           category=category)


@app.route('/categories/<int:cat_id>', methods=['POST'])
def delete_category(cat_id):
    category = c.query(Category).filter_by(id=cat_id).first()

    c.delete(category)
    c.commit()

    return redirect(url_for('get_categories'))


# AUTH

@app.route('/login', methods=['GET'])
def show_login():
    """Get the login page with a generated random state variable."""
    # If the user is already logged in, redirect them.
    if 'username' in session:
        flash("You're already logged in. Disconnect first.")
        return redirect(url_for('get_gifts'))

    # Generate a random string of 32 uppercase letters and digits
    choice = string.ascii_uppercase + string.digits
    chars = [random.choice(choice) for x in xrange(32)]
    state = ''.join(chars)

    # store that random string in the session
    session['state'] = state

    return render_template('login.html',
                           STATE=session['state'],
                           user='logging in')


@app.route('/gconnect', methods=['GET', 'POST'])
def gconnect():
    """Login and/or register a user using Google OAuth."""
    # Check if the posted STATE matches the session state
    if request.args.get('state') != session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'

        return response

    # Get the token sent through ajax
    token = request.data

    # Verify it
    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        idinfo = id_token.verify_oauth2_token(token, g_requests.Request(), CLIENT_ID)

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            # Wrong issuer
            message = 'Wrong issuer.'
            response = make_response(json.dumps(message), 401)
            response.headers['Content-Type'] = 'application/json'

            return response

    except ValueError:
        # Invalid token
        message = 'Invalid token.'
        response = make_response(json.dumps(message), 401)
        response.headers['Content-Type'] = 'application/json'

        return response

    # ID token is valid. Get the user's Google Account ID from the decoded token.
    gplus_id = idinfo['sub']

    # Check that our client's id matches that of the token
    # returned by Google API's server
    if idinfo['aud'] != CLIENT_ID:
        message = "Token's client ID does not match this app's."
        response = make_response(json.dumps(message), 401)
        response.headers['Content-Type'] = 'application/json'

        return response

    # Verify that the user's NOT ALREADY LOGGED IN

    # Get the access token stored in the session if there is one
    stored_token = session.get('token')
    # Get the user id stored in the session if there is one
    stored_gplus_id = session.get('gplus_id')

    # Check if there is already an access token in the session
    # and if so, if the id of the token from the CREDENTIALS OBJECT
    # matches the id stored in the session
    if stored_token is not None and gplus_id == stored_gplus_id:
        print 'Current user is already connected.'

        return make_response(render_template('login_success.html',
                                             user=serialize_session_user()))

    # If we get this far, the access token is VALID
    # and it's THE RIGHT ACCESS TOKEN.
    # The user can be successfully logged in

    # 1. Store the access token in the session
    session['token'] = token
    session['gplus_id'] = gplus_id

    # 3. Store user info in the session
    session['username'] = idinfo['name']
    session['picture'] = idinfo['picture']
    session['email'] = idinfo['email']

    # Specify we used Google to sign in
    session['provider'] = 'google'

    return make_response(render_template('login_success.html',
                                         user=serialize_session_user()))


# HELPERS

def serialize_session_user():
    """Return a dictionary containing a user's info from session."""
    return {'username': session.get('username'),
            'email': session.get('email'),
            'picture': session.get('picture'),
            'id': session.get('user_id')}


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.debug = True
    app.run(port=8080)
