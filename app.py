from flask import Flask, request, render_template, redirect, url_for, flash
from flask_login import (
    LoginManager, UserMixin, current_user,
    logout_user, login_user, login_required
)

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from flask_wtf import FlaskForm
from wtforms import SubmitField, BooleanField, StringField, PasswordField, TextAreaField, FloatField
from wtforms.validators import DataRequired, ValidationError, EqualTo
from flask_bcrypt import Bcrypt
from flask_wtf.file import FileField, FileAllowed

import os
from datetime import datetime
from sqlalchemy import DateTime

import secrets
from PIL import Image

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView


basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
key = 'blablablaverysecure'

app.config['SECRET_KEY'] = key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

bcrypt = Bcrypt(app)


class ManoModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.el_pastas == 'labas@kristina.lt'


admin = Admin(app)


class Vartotojas(db.Model, UserMixin):
    __tablename__ = "vartotojas"
    id = db.Column(db.Integer, primary_key=True)
    vardas = db.Column("Vardas", db.String(20), unique=True, nullable=False)
    el_pastas = db.Column("El. pašto adresas", db.String(120), unique=True, nullable=False)
    nuotrauka = db.Column(db.String(20), nullable=False, default='default.jpeg')
    slaptazodis = db.Column("Slaptažodis", db.String(60), unique=True, nullable=False)


class Irasas(db.Model):
    __tablename__ = "irasas"
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column("Data", DateTime, default=datetime.now())
    pajamos = db.Column("Pajamos", db.Boolean)
    suma = db.Column("Vardas", db.Integer)
    vartotojas_id = db.Column(db.Integer, db.ForeignKey("vartotojas.id"))
    vartotojas = db.relationship("Vartotojas", lazy=True)


admin.add_view(ManoModelView(Vartotojas, db.session))
admin.add_view(ModelView(Irasas, db.session))


@login_manager.user_loader
def load_user(vartotojo_id):
    return Vartotojas.query.get(int(vartotojo_id))


class RegistracijosForma(FlaskForm):
    vardas = StringField('Vardas', [DataRequired()])
    el_pastas = StringField('El. paštas', [DataRequired()])
    slaptazodis = PasswordField('Slaptažodis', [DataRequired()])
    patvirtintas_slaptazodis = PasswordField("Pakartokite slaptažodį", [EqualTo('slaptazodis', "Slaptažodis turi sutapti.")])
    submit = SubmitField('Prisiregistruoti')

    def validate_vardas(self, vardas):
        vartotojas = Vartotojas.query.filter_by(vardas=vardas.data).first()
        if vartotojas:
            raise ValidationError('Šis vardas panaudotas. Pasirinkite kitą.')

    def validate_pastas(self, el_pastas):
        vartotojas = Vartotojas.query.filter_by(el_pastas=el_pastas.data).first()
        if vartotojas:
            raise ValidationError('Šis el. pašto adresas panaudotas. Pasirinkite kitą.')


class PrisijungimoForma(FlaskForm):
    el_pastas = StringField('El. paštas', [DataRequired()])
    slaptazodis = PasswordField('Slaptažodis', [DataRequired()])
    prisiminti = BooleanField("Prisiminti mane")
    submit = SubmitField('Prisijungti')


class PaskyrosAtnaujinimoForma(FlaskForm):
    vardas = StringField('Vardas', [DataRequired()])
    el_pastas = StringField('El. paštas', [DataRequired()])
    nuotrauka = FileField('Atnaujinti profilio nuotrauką', validators=[FileAllowed(['jpg', 'jpeg', 'png'])])
    submit = SubmitField('Atnaujinti')

    def validate_vardas(self, vardas):
        if vardas.data != current_user.vardas:
            vartotojas = Vartotojas.query.filter_by(vardas=vardas.data).first()
            if vartotojas:
                raise ValidationError('Šis vardas panaudotas. Pasirinkite kitą.')

    def validate_pastas(self, el_pastas):
        if el_pastas.data != current_user.el_pastas:
            vartotojas = Vartotojas.query.filter_by(el_pastas=el_pastas.data).first()
            if vartotojas:
                raise ValidationError('Šis el. pašto adresas panaudotas. Pasirinkite kitą.')


class IrasasForm(FlaskForm):
    pajamos = BooleanField('Pajamos')
    suma = FloatField('Suma', [DataRequired()])
    submit = SubmitField('Įvesti')


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profilio_nuotraukos', picture_fn)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn


@app.route('/')
def home():
    return render_template('index.html')


@app.route("/registruotis", methods=['GET', 'POST'])
def registruotis():
    db.create_all()
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistracijosForma()
    if form.validate_on_submit():
        koduotas_slaptazodis = bcrypt.generate_password_hash(form.slaptazodis.data).decode('utf-8')
        vartotojas = Vartotojas(vardas=form.vardas.data, el_pastas=form.el_pastas.data, slaptazodis=koduotas_slaptazodis)
        db.session.add(vartotojas)
        db.session.commit()
        flash('Sėkmingai prisiregistravote! Galite prisijungti', 'success')
        return redirect(url_for('home'))
    return render_template('registruotis.html', title='Register', form=form)


@app.route("/prisijungti", methods=['GET', 'POST'])
def prisijungti():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = PrisijungimoForma()
    if form.validate_on_submit():
        user = Vartotojas.query.filter_by(el_pastas=form.el_pastas.data).first()
        if user and bcrypt.check_password_hash(user.slaptazodis, form.slaptazodis.data):
            login_user(user, remember=form.prisiminti.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Prisijungti nepavyko. Patikrinkite el. paštą ir slaptažodį', 'danger')
    return render_template('prisijungti.html', title='Prisijungti', form=form)


@app.route("/atsijungti")
def atsijungti():
    logout_user()
    return redirect(url_for('home'))


@app.route("/irasai")
@login_required
def records():
    db.create_all()
    page = request.args.get('page', 1, type=int)
    visi_irasai = Irasas.query.filter_by(vartotojas_id=current_user.id).order_by(Irasas.data.desc()).paginate(page=page, per_page=5)
    return render_template("irasai.html", visi_irasai=visi_irasai, datetime=datetime)


@app.route("/naujas_irasas", methods=["GET", "POST"])
def new_record():
    db.create_all()
    forma = IrasasForm()
    if forma.validate_on_submit():
        naujas_irasas = Irasas(pajamos=forma.pajamos.data, suma=forma.suma.data, vartotojas_id=current_user.id)
        db.session.add(naujas_irasas)
        db.session.commit()
        flash(f"Įrašas sukurtas", 'success')
        return redirect(url_for('records'))
    return render_template("prideti_irasa.html", form=forma)


@app.route("/paskyra", methods=['GET', 'POST'])
@login_required
def paskyra():
    form = PaskyrosAtnaujinimoForma()
    if form.validate_on_submit():
        if form.nuotrauka.data:
            nuotrauka = save_picture(form.nuotrauka.data)
            current_user.nuotrauka = nuotrauka
        current_user.vardas = form.vardas.data
        current_user.el_pastas = form.el_pastas.data
        db.session.commit()
        flash('Tavo paskyra atnaujinta!', 'success')
        return redirect(url_for('paskyra'))
    elif request.method == 'GET':
        form.vardas.data = current_user.vardas
        form.el_pastas.data = current_user.el_pastas
    if current_user.nuotrauka:
        nuotrauka = url_for('static', filename='profilio_nuotraukos/' + current_user.nuotrauka)
    else:
        nuotrauka = url_for('static', filename='profilio_nuotraukos/default.jpeg')
    return render_template('paskyra.html', title='Account', form=form, nuotrauka=nuotrauka)


@app.route("/delete/<int:id>")
def delete(id):
    irasas = Irasas.query.get(id)
    db.session.delete(irasas)
    db.session.commit()
    return redirect(url_for('records'))


@app.route("/update/<int:id>", methods=['GET', 'POST'])
def update(id):
    forma = IrasasForm()
    irasas = Irasas.query.get(id)
    if forma.validate_on_submit():
        irasas.pajamos = forma.pajamos.data
        irasas.suma = forma.suma.data
        db.session.commit()
        return redirect(url_for('records'))
    return render_template("update.html", form=forma, irasas=irasas)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=7000, debug=True)
