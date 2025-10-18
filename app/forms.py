from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import IntegerField, DecimalField, BooleanField, StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange, InputRequired, ValidationError
from .repositories import MonthlyBillRepository


class MonthForm(FlaskForm):
    year = IntegerField("Year", validators=[InputRequired(), NumberRange(min=2000, max=3000)])
    month = SelectField(
        "Month",
        choices=[
            (1, "January"), (2, "February"), (3, "March"), (4, "April"),
            (5, "May"), (6, "June"), (7, "July"), (8, "August"),
            (9, "September"), (10, "October"), (11, "November"), (12, "December"),
        ],
        coerce=int,
        validators=[InputRequired()],
    )

    def validate_month(self, field):
        # Only perform duplicate check when explicitly enabled by the route
        if not getattr(self, 'check_duplicates', False):
            return
        year = self.year.data
        month = self.month.data
        if year is None or month is None:
            return
        repo = MonthlyBillRepository()
        if repo.find_by_year_month(int(year), int(month)):
            raise ValidationError(f"A month for {year}-{int(month):02d} already exists.")
    electricity_amount = DecimalField("Electricity", validators=[InputRequired(), NumberRange(min=0)])
    water_amount = DecimalField("Water", validators=[InputRequired(), NumberRange(min=0)])
    internet_amount = DecimalField("Internet", validators=[InputRequired(), NumberRange(min=0)])
    submit = SubmitField("Save")
