from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np
import pandas as pd
import joblib
import sklearn
from datetime import datetime
app = Flask(__name__)

# 允许来自所有域的跨域请求
CORS(app, support_credentials=True)



# 配置 MySQL 数据库连接
# 确保数据库 URI 正确，根据您提供的 MySQL 信息进行调整
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://crophistory:WKU12345cps@121.199.172.86/crophistory'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
model = joblib.load('random_forest_model.pkl')
encoder = joblib.load('label_encoder.pkl')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
@app.route('/test_connection', methods=['GET'])
def test_connection():
    return 'Server is reachable.'

@app.route('/test_cors', methods=['GET'])
def test_cors():
    response = jsonify({'message': 'CORS test successful.'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response
# 创建数据库表格（如果尚未创建）
from flask import Flask, request, jsonify
from models import History  # 确保你有一个正确的模型定义
from db_setup import db   # 确保数据库设置正确

@app.route('/get_history', methods=['GET'])
def get_history():
    try:
        # 查询数据库中的所有历史记录
        history_records = History.query.all()
        # 序列化数据为JSON格式
        history_list = [{
            'historyID': record.historyID,
            'accountID': record.accountID,
            'pHValue': record.pHValue,
            'nitrogen': record.nitrogen,
            'phosphorus': record.phosphorus,
            'potassium': record.potassium,
            'temperature': record.temperature,
            'humidity': record.humidity,
            'rainfall': record.rainfall,
            'label': record.label,
            'recordDate': record.recordDate.strftime("%Y-%m-%d %H:%M:%S")  # 格式化日期时间
        } for record in history_records]
        return jsonify(history_list), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch history records: {}'.format(str(e))}), 500


@app.before_request
def create_tables():
    db.create_all()
@app.route("/")
def hello_world():
    return "Hello, cross-origin world!"
# 创建新用户
@app.route('/user', methods=['POST'])
def create_user():
    data = request.json
    if 'username' not in data or 'password' not in data:
        return jsonify({"message": "Missing username or password"}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"message": "Username already exists"}), 400
    new_user = User(username=data['username'])
    new_user.password = data['password']
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created"}), 201

# 获取所有用户
@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{'id': user.id, 'username': user.username} for user in users])

# 更新用户
@app.route('/user/<int:id>', methods=['PUT'])
def update_user(id):
    data = request.json
    user = User.query.filter_by(id=id).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    if 'username' in data:
        user.username = data['username']
    if 'password' in data:
        user.password = data['password']
    db.session.commit()
    return jsonify({"message": "User updated"})

# 删除用户
@app.route('/user/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.filter_by(id=id).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"})

class SoilData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nitrogen = db.Column(db.Float, nullable=False)
    phosphorus = db.Column(db.Float, nullable=False)
    potassium = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    ph = db.Column(db.Float, nullable=False)
    rainfall = db.Column(db.Float, nullable=False)
class History(db.Model):
    __tablename__ = 'history'
    historyID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    accountID = db.Column(db.Integer, nullable=False)
    pHValue = db.Column(db.Float, nullable=False)
    nitrogen = db.Column(db.Float, nullable=False)
    phosphorus = db.Column(db.Float, nullable=False)
    potassium = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    rainfall = db.Column(db.Float, nullable=False)
    label = db.Column(db.Text, nullable=False)
    recordDate = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


@app.route('/get_crop_recommendation', methods=['POST'])
def get_crop_recommendation():
    data = request.json
    try:
        # 创建历史记录
        new_record = History(
            accountID=1,
            pHValue=data['ph'],
            nitrogen=data['nitrogen'],
            phosphorus=data['phosphorus'],
            potassium=data['potassium'],
            temperature=data['temperature'],
            humidity=data['humidity'],
            rainfall=data['rainfall'],
            label='',  # 将在预测后设置
            recordDate=datetime.utcnow()
        )

        # 进行预测
        model = joblib.load('random_forest_model.pkl')
        encoder = joblib.load('label_encoder.pkl')
        input_data = np.array([[data['nitrogen'], data['phosphorus'], data['potassium'], data['temperature'], data['humidity'], data['ph'], data['rainfall']]])
        prediction = model.predict(input_data)
        predicted_label = encoder.inverse_transform(prediction)[0]

        # 更新记录的作物标签
        new_record.label = predicted_label

        # 保存记录到数据库
        db.session.add(new_record)
        db.session.commit()

        return jsonify({"recommended_crop": predicted_label}), 200
    except KeyError as e:
        # 如果缺少必要的字段，返回错误信息
        return jsonify({"error": f"Missing data for required field: {str(e)}"}), 400
    except Exception as e:
        # 处理其他可能的错误
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



