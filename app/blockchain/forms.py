from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, FloatField, StringField
from wtforms.validators import Required, NumberRange


class TransactionForm(FlaskForm):
    sender = TextAreaField('Sender', validators=[Required()])
    recipient = TextAreaField('Recipient', validators=[Required()])
    amount = FloatField('Amount', validators=[Required(), NumberRange(0, )])
    private_key = TextAreaField('Private Key', validators=[Required()])
    submit = SubmitField('Submit')


class BindWalletForm(FlaskForm):
    wallet_address = TextAreaField('Wallet Address', validators=[Required()])
    bind = SubmitField('Bind')


class WalletBalanceForm(FlaskForm):
    wallet_address = TextAreaField('Wallet Address', validators=[Required()])
    search = SubmitField('Search')
