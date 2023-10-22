WARNING! This is my first project, so please expect many bugs and bad coding!
The web app is currently in German.
I published it here, maybe someone find it useful.

I wrote a flask app to manage a car with its costs with some statistics (fillups, taxes, insurance, repairs, multiple users and cars).

Screenshots
![Übersicht.png](assets%2F%C3%9Cbersicht.png)
![Grafiken.png](assets%2FGrafiken.png)
![Kostenübersicht.png](assets%2FKosten%C3%BCbersicht.png)
![Tanken.png](assets%2FTanken.png)
![Wartungsintervall.png](assets%2FWartungsintervall.png)

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

# default admin user in sqlite fuel.db admin:admin123
python3 -c 'import bcrypt; print(bcrypt.hashpw(b"YOUR_SECRET_PASSWORD", bcrypt.gensalt()).decode("utf-8"))'
# then edit sqlite and change password_hash
# at /user you can create new users
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
# in the existing fuel.db are some dummy data for the user admin:admin123
# at /user you can create new users
flask run --debug --no-debugger
```




