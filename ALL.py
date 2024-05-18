from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import hashlib
import numpy as np
import joblib

app = Flask(__name__)
CORS(app)

# 配置 MySQL 数据库连接
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://crophistory:WKU12345cps@121.199.172.86/crophistory'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 用户模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # 将密码字段名改为 pass
    email = db.Column(db.String(120), unique=True, nullable=False)
    registertime = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<User {self.name}>'

# 农作物预测模型
class SoilData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nitrogen = db.Column(db.Float, nullable=False)
    phosphorus = db.Column(db.Float, nullable=False)
    potassium = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    ph = db.Column(db.Float, nullable=False)
    rainfall = db.Column(db.Float, nullable=False)

# 设置静态文件夹路径
static_folder_path = '../login-system-main'

@app.route('/')
def index():
    # 返回登录页面
    return send_from_directory(static_folder_path, 'login.html')

@app.route('/<path:filename>')
def serve_static(filename):
    # 返回静态资源文件
    return send_from_directory(static_folder_path, filename)

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    password = request.form['password']
    email = request.form['email']

    # 检查用户名和邮箱是否已存在
    if User.query.filter_by(name=name).first() is not None:
        return jsonify({'error': 'Username already exists'}), 400
    if User.query.filter_by(email=email).first() is not None:
        return jsonify({'error': 'Email already exists'}), 400

    # 创建用户对象并添加到数据库
    # hashed_password = hashlib.sha256(password.encode()).hexdigest()  # 使用 SHA256 对密码进行哈希加密
    new_user = User(name=name, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Registration successful'}), 200

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    # 根据邮箱查询用户
    user = User.query.filter_by(email=email).first()

    if user is None:
        return jsonify({'error': 'User not found'}), 404

    # 验证密码
    if hashlib.sha256(password.encode()).hexdigest() != user.password:
        return jsonify({'error': 'Incorrect password'}), 401

    # 登录成功后重定向到农作物预测页面
    return redirect('/soil_data')

@app.route('/soil_data')
def soil_data():
    # 返回农作物预测页面
    return send_from_directory(static_folder_path, 'main.html')

@app.route('/get_crop_recommendation', methods=['POST'])
def get_crop_recommendation():
    # 获取通过POST请求发送的数据
    data = request.json
    # 调用预测函数
    recommended_crop = predict_crop(
        data['nitrogen'],
        data['phosphorus'],
        data['potassium'],
        data['temperature'],
        data['humidity'],
        data['ph'],
        data['rainfall']
    )
    # 返回预测结果
    return jsonify({"recommended_crop": recommended_crop})

def predict_crop(N, P, K, temperature, humidity, ph, rainfall):
    # 加载模型
    model = joblib.load('random_forest_model.pkl')
    # 加载标签编码器
    encoder = joblib.load('label_encoder.pkl')

    # 构建输入数据
    data = np.array([[N, P, K, temperature, humidity, ph, rainfall]])
    # 进行预测
    prediction = model.predict(data)
    # 获取预测结果的标签
    predicted_label = encoder.inverse_transform(prediction)[0]

    return predicted_label

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True)
