WARNING! This is my first project, so please expect many bugs and bad coding!
The web app is currently in German.
I published it here, maybe someone find it useful.

I wrote a flask app to manage a car with its costs with some statistics (fillups, taxes, insurance, repairs, multiple users and cars).

### install requirements
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### fix error in flask-login, until new fixed version is available
```
sed -i "s/from werkzeug.urls import url_decode/from urllib.parse import unquote/" venv/lib/python3.10/site-packages/flask_login/utils.py
sed -i "s/from werkzeug.urls import url_encode/from urllib.parse import urlencode/" venv/lib/python3.10/site-packages/flask_login/utils.py
sed -i "s/md = url_decode(parsed_result.query)/md = unquote(parsed_result.query)/" venv/lib/python3.10/site-packages/flask_login/utils.py
sed -i "s/netloc=netloc, query=url_encode(md, sort=True)/netloc=netloc, query=urlencode(md, sort=True)/" venv/lib/python3.10/site-packages/flask_login/utils.py
```

### edit required variables
```
cp example.env .env
# manually edit env, if you want to use mysql db
sed -i "s/REPLACE_SECRET_KEY/$(openssl rand -base64 30)/" .env
sed -i "s/REPLACE_WTF_CSRF_SECRET_KEY/$(openssl rand -base64 30)/" .env

sed -i "s/replace_user1/YOUR_USERNAME/" app.py
BCRYPT_PASSWORD_HASH=$(python3 -c 'import bcrypt; print(bcrypt.hashpw(b"YOUR_SECRET_PASSWORD", bcrypt.gensalt()).decode("utf-8"))')
sed -i "s/replace_password1/$BCRYPT_PASSWORD_HASH/" app.py
```

### download used libs
```
wget https://raw.githubusercontent.com/javve/list.js/v2.3.1/dist/list.min.js -O list.min.js

wget https://download.amcharts.com/5.4/amcharts_5.4.11.zip -O amcharts_5.4.11.zip
unzip amcharts_5.4.11.zip

wget https://github.com/jgthms/bulma/releases/download/0.9.4/bulma-0.9.4.zip -O bulma-0.9.4.zip
unzip bulma-0.9.4.zip -d httpdocs
```


### start
```
# local run with sqlite
# in the existing fuel.db are some dummy data for the user with name "YOUR_USERNAME"
flask run --debug --no-debugger
```




