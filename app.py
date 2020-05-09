from flask import Flask
from majavahbot.web.blueprint import blueprint

app = Flask(__name__, template_folder='majavahbot/web/templates')
app.register_blueprint(blueprint)

if __name__ == '__main__':
    app.run()
