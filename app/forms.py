from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import IntegerField, DecimalField, BooleanField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, InputRequired


class MonthForm(FlaskForm):
    year = IntegerField("Year", validators=[InputRequired(), NumberRange(min=2000, max=3000)])
    month = IntegerField("Month", validators=[InputRequired(), NumberRange(min=1, max=12)])
    electricity_amount = DecimalField("Electricity", validators=[InputRequired(), NumberRange(min=0)])
    water_amount = DecimalField("Water", validators=[InputRequired(), NumberRange(min=0)])
    internet_amount = DecimalField("Internet", validators=[InputRequired(), NumberRange(min=0)])
    submit = SubmitField("Save")
