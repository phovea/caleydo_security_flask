__author__ = 'Samuel Gratzl'

import caleydo_server.security as security

import flask.ext.login as login

class User(security.User, login.UserMixin):
  def __init__(self, id):
    self.id = id
    pass

  def get_id(self):
    try:
        return unicode(self.id)  # python 2
    except NameError:
        return str(self.id)  # python 3

class UserStore(object):
  def __init__(self):
    pass

  def load(self, id):
    return None

  def load_from_key(self, api_key):
    return None

  def login(self, username, extra_fields = {}):
    return None

  def logout(self, user):
    pass

class FlaskLoginManager(security.SecurityManager):
  def __init__(self):
    super(FlaskLoginManager, self).__init__()
    self._manager = login.LoginManager()
    self._manager.user_loader(self._load_user)
    self._manager.request_loader(self._load_user_from_request)
    self._manager.login_view = None

    import caleydo_server.plugin as plugin
    self._user_stores = [p.load().factory()  for p in plugin.list('user_stores')]
    if len(self._user_stores) == 0:
      import dummy_store
      self._user_stores.append(dummy_store.create())

  def _load_user(self, id):
    for store in self._user_stores:
      u = store.load(id)
      if u:
        return u
    return None
  #  return User.query.get(int(id))

  def init_app(self, app):
    self._manager.init_app(app)

  def add_login_routes(self, app):
    import flask

    @app.route('/login', methods=['GET', 'POST'])
    def login():
      if flask.request.method == 'POST':
        user = flask.request.values['username']
        user_obj = self.login(user, flask.request.values)
        if not user_obj:
          return flask.abort(401)  # 401 Unauthorized
        print 'user login: '+user
        return flask.jsonify(name=user_obj.name,roles=user_obj.roles)

      #return a login mask
      login_mask = """
      <!DOCTYPE html>
      <html>
      <body>
        <form name="login" action="/login" method="post" accept-charset="utf-8">
          <div><label for="username">User name: </label><input type="text" name="username" placeholder="name" required="required"></div>
          <div><label for="password">Password</label><input type="password" name="password" placeholder="password" required="required"></div>
          <div><input type="reset" value="Reset"><input type="submit" value="Login"></div>
        </form>
      </body>
      </html>
      """
      return flask.render_template_string(login_mask)

    @app.route('/logout', methods=['POST'])
    def logout():
      self.logout()
      return 'Bye Bye'

  def login_required(self, f):
    return self._manager.login_required(f)

  @property
  def current_user(self):
    return login.current_user

  def logout(self):
    u = self.current_user
    print 'user logout: '+u.name
    for store in self._user_stores:
      store.logout(u)
    login.logout_user()

  def login(self, username, extra_fields = {}):
    for store in self._user_stores:
      u = store.login(username, extra_fields)
      if u:
        login.login_user(u)
        return u
    return None

  def _load_user_from_key(self, api_key):
    for store in self._user_stores:
      u = store.load_from_key(api_key)
      if u:
        return u

  def _load_user_from_request(self, request):
    # first, try to login using the api_key url arg
    api_key = request.args.get('api_key')
    if api_key:
      user = self._load_user_from_key(api_key)
      if user:
        return user

    # next, try to login using Basic Auth
    api_key = request.headers.get('Authorization')
    if api_key:
      api_key = api_key.replace('Basic ', '', 1)
      try:
        import base64
        api_key = base64.b64decode(api_key)
      except TypeError:
        pass
      user = self._load_user_from_key(api_key)
      if user:
        return user

    # finally, return None if both methods did not login the user
    return None

def create():
  return FlaskLoginManager()