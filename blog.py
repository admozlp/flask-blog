import re
from MySQLdb import cursors
from flask import Flask,render_template,flash,redirect,url_for,session,logging,request,make_response
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField, form,validators
from passlib.hash import sha256_crypt
from functools import wraps
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "flaskblog"


app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "flaskblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql =  MySQL(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfaya ulaşmak için giriş yapmalısınız","danger")
            return redirect(url_for("login"))
    return decorated_function

class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.length(max = 20,min= 3)])
    username = StringField("Kullanıcı Adı",validators=[validators.length(max=20,min=3)])
    email = StringField("E mail Adresi",validators=[validators.Email(message="Lütfen Geçerli Bir E Mail Adresi Giriniz.")])
    password = PasswordField("Parola",validators=[validators.required("Lütfen Bir Parola Belirleyin."),
    validators.EqualTo(fieldname="confirm",message="Parolaız Uyuşmuyor.")
    ])
    confirm = PasswordField("Parola Doğrula")

class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

class Article(Form):
    title = StringField("Başlık",validators=[validators.length(min=3,max=50)])
    content = TextAreaField("İçerik",validators=[validators.length(min=5)])

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data.strip()
        username = form.username.data.strip()
        email = form.email.data.strip()
        password = sha256_crypt.encrypt(form.password.data).strip()


        cursor = mysql.connection.cursor()
        sorgu1 = "select * from users where username = %s"
        result = cursor.execute(sorgu1,(username,))

        if result > 0:
            return redirect(url_for("register"))
        else:
            sorgu2 = "insert into users (name,username,email,password) values (%s,%s,%s,%s)"
            cursor.execute(sorgu2,(name,username,email,password))
            mysql.connection.commit()
            cursor.close()
            flash("Kayıt Başarıyla Yapıldı. Giriş Yapabilirsiniz.","success")
            return redirect(url_for("login"))
    return render_template("register.html",form = form)


@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)

    if request.method == "POST" and form.validate():
        username = form.username.data.strip()
        password = form.password.data.strip()
        
        sorgu1 = "select * from users where username = %s"
        cursor = mysql.connection.cursor()
        res = cursor.execute(sorgu1,(username,))

        if res> 0:
            data  = cursor.fetchone()
            real_pass = data["password"]

            if sha256_crypt.verify(password,real_pass):
                session["username"] = username
                session["logged_in"] = True
                flash("Giriş Yapıldı","success")
                return redirect(url_for("index"))

    return render_template("login.html",form = form)


@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles where author = %s"
    res = cursor.execute(sorgu,(session["username"],))
    if res > 0:
        articles =  cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    return render_template("dashboard.html")

@app.route("/addarticle",methods = ["GET","POST"])
@login_required
def addarticle():
    form = Article(request.form)

    if request.method == "POST" and form.validate():
        title = form.title.data
        content =form.content.data

        cursor = mysql.connection.cursor()

        sorgu = "insert into articles (author,title,content) values (%s,%s,%s)"
        cursor.execute(sorgu,(session["username"],title,content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale Başarıyla Kaydedildi","success")
        return redirect(url_for("dashboard"))


    return render_template("addarticle.html",form = form)

@app.route("/detail/<string:id>")
def detail(id):
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles where id = %s"
    res = cursor.execute(sorgu,(id,))
    
    if res > 0:
        article = cursor.fetchone()
        return render_template("detail.html",article = article)
    

@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles where id = %s"
    res = cursor.execute(sorgu,(id,))
    if res > 0:
        sorgu2 = "delete from articles where id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        flash("Makale Silindi","success")
        return redirect(url_for("dashboard"))

    return redirect(url_for("index"))


@app.route("/update/<string:id>",methods = ["GET","POST"])
@login_required
def update(id): 
    cursor = mysql.connection.cursor()

    if request.method  == "GET":
        sorgu = "select * from articles where id = %s"
        res = cursor.execute(sorgu,(id,))
        if res > 0:
            form = Article()
            article = cursor.fetchone()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form = form)
        
    form = Article(request.form)
    title = form.title.data
    content = form.content.data

    sorgu2 = "update articles set title = %s, content = %s"
    cursor.execute(sorgu2,(title,content))
    mysql.connection.commit()
    flash("Makale Güncellendi","success")
    return redirect(url_for("dashboard"))

@app.route("/allarticles")
def allarticle():
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles"
    res = cursor.execute(sorgu)
    if res > 0:
        articles = cursor.fetchall()
        return render_template("allarticles.html",articles = articles)
    
@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Çıkış Yapıldı","success")
    return redirect(url_for("index"))

@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor= mysql.connection.cursor()
        sorgu = "select * from articles where title like '%"+keyword+"%' "
        res = cursor.execute(sorgu)
        if res > 0:
            response = cursor.fetchall()
            return render_template("search.html",response = response)
        else:
            flash("Böyle Bir Makale Bulunmuyor.","danger")
            return redirect(url_for("allarticles"))
        
    
if __name__ == "__main__":
    app.run(debug=True)