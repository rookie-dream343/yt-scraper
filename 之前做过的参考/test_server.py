#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的Flask服务器测试
"""

from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "测试API"
    })

@app.route('/', methods=['GET'])
def home():
    """首页"""
    return jsonify({
        "message": "Dify工作流后端API服务",
        "endpoints": {
            "health": "/health",
            "process_video": "/process_video"
        }
    })

if __name__ == '__main__':
    print("启动测试服务器...")
    print("服务地址: http://localhost:5000")
    print("健康检查: http://localhost:5000/health")
    app.run(host='0.0.0.0', port=5000, debug=False) 