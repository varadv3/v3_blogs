from flask import render_template
from app import app, db
# from .email import send_internal_server_error

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error_404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    # print('Hello Error 505')
    # send_internal_server_error()
    return render_template('error_500.html'), 500