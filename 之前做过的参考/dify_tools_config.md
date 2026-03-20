# Dify工作流配置指南

## 📋 概述
本指南将帮助您在Dify中配置YouTube视频下载和字幕处理工作流。

## 🚀 第一步：启动后端API服务

### 1. 安装依赖
```bash
pip install flask
```

### 2. 启动API服务
双击运行 `start_dify_worker.bat` 或在命令行中运行：
```bash
cd 炉子
python dify_worker.py
```

### 3. 验证服务
访问 http://localhost:5000/health 确认服务正常运行

## 🔧 第二步：在Dify中配置工具

### 1. 创建API工具

#### 工具1：视频下载处理器
- **工具名称**: YouTube视频下载器
- **API Endpoint**: `http://localhost:5000/process_video`
- **Method**: `POST`
- **Headers**: 
  - `Content-Type: application/json`
- **Body**:
```json
{
  "url": "{{url}}",
  "quality": "{{quality}}",
  "languages": {{languages}},
  "embed_subtitles": {{embed_subtitles}}
}
```

#### 工具2：字幕下载器
- **工具名称**: YouTube字幕下载器
- **API Endpoint**: `http://localhost:5000/download_subtitles`
- **Method**: `POST`
- **Headers**: 
  - `Content-Type: application/json`
- **Body**:
```json
{
  "url": "{{url}}",
  "languages": {{languages}}
}
```

#### 工具3：任务状态查询器
- **工具名称**: 任务状态查询器
- **API Endpoint**: `http://localhost:5000/task_status/{{task_id}}`
- **Method**: `GET`
- **Headers**: 无

### 2. 配置输入参数

#### 视频下载器参数：
- `url` (string, required): YouTube视频URL
- `quality` (string, optional): 视频质量 (1080p, 720p, 480p, 4k, best)
- `languages` (array, optional): 字幕语言列表
- `embed_subtitles` (boolean, optional): 是否嵌入字幕

#### 字幕下载器参数：
- `url` (string, required): YouTube视频URL
- `languages` (array, optional): 字幕语言列表

#### 任务状态查询器参数：
- `task_id` (string, required): 任务ID

## 📊 第三步：创建工作流

### 1. 创建应用变量
- `youtube_url` (string): YouTube视频链接
- `video_quality` (string): 视频质量选择
- `subtitle_languages` (array): 字幕语言选择
- `embed_subtitles` (boolean): 是否嵌入字幕

### 2. 设计工作流节点

#### 节点1：开始节点
- 接收用户输入的YouTube URL

#### 节点2：视频下载工具
- 调用YouTube视频下载器
- 输入：用户提供的URL和参数
- 输出：任务ID和状态

#### 节点3：LLM处理节点
- 处理API响应
- 生成用户友好的回复
- 提示词示例：
```
你是一个视频处理助手。用户想要下载YouTube视频并处理字幕。

API返回了以下信息：
{{api_tool_output}}

请根据返回的信息，生成一段友好、清晰的中文回复给用户。
如果任务成功，请告诉用户文件保存位置和下载的内容。
如果任务失败，请提供有用的错误信息和解决建议。
```

#### 节点4：结束节点
- 返回处理结果给用户

## 🎯 第四步：测试工作流

### 1. 测试用例
```
用户输入：https://www.youtube.com/watch?v=2YYjPs8t8MI
期望输出：视频下载和字幕处理完成，文件保存在downloads文件夹
```

### 2. 工作流逻辑
1. 用户输入YouTube URL
2. Dify调用后端API启动下载任务
3. 后端异步处理视频下载和字幕处理
4. 返回任务状态和结果
5. LLM生成友好回复
6. 用户获得处理结果

## 🔍 API接口说明

### POST /process_video
启动视频下载和字幕处理任务

**请求体**:
```json
{
  "url": "https://www.youtube.com/watch?v=xxx",
  "quality": "1080p",
  "languages": ["en", "zh-Hans", "ja"],
  "embed_subtitles": true
}
```

**响应**:
```json
{
  "status": "success",
  "message": "视频处理任务已启动",
  "task_id": "20250805123456",
  "task_status_url": "/task_status/20250805123456"
}
```

### GET /task_status/{task_id}
查询任务状态

**响应**:
```json
{
  "task_id": "20250805123456",
  "status": "completed",
  "progress": "处理完成",
  "result": {
    "title": "视频标题",
    "video_file": "downloads/视频标题.mp4",
    "subtitle_files": ["downloads/视频标题.en.srt"],
    "message": "视频下载和字幕处理完成！"
  },
  "created_at": "2025-08-05T12:34:56"
}
```

### POST /download_subtitles
只下载字幕文件

**请求体**:
```json
{
  "url": "https://www.youtube.com/watch?v=xxx",
  "languages": ["en", "zh-Hans"]
}
```

## 🛠️ 故障排除

### 1. API服务无法启动
- 检查Flask是否安装：`pip install flask`
- 检查端口5000是否被占用
- 查看错误日志

### 2. Dify无法连接API
- 确认API服务正在运行
- 检查网络连接
- 验证API端点URL正确

### 3. 下载失败
- 检查YouTube URL是否有效
- 确认网络连接正常
- 查看后端日志获取详细错误信息

## 📝 注意事项

1. **网络要求**: 确保服务器能访问YouTube
2. **存储空间**: 确保有足够的磁盘空间存储视频文件
3. **并发限制**: 建议同时处理的任务数量不超过3个
4. **日志管理**: 定期清理日志文件避免占用过多空间 