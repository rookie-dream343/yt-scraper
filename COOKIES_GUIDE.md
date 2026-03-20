# 如何获取 cookies.txt 文件

如果从浏览器读取cookies失败，可以使用cookies.txt文件方式。

## 方法1: 使用浏览器扩展 (推荐)

### Chrome/Edge
1. 安装 "Get cookies.txt" 扩展
   - Chrome 网上应用店搜索: "Get cookies.txt"
   - 或访问: https://chrome.google.com/webstore

2. 安装后点击扩展图标

3. 选择当前域 (youtube.com)

4. 点击 "Export" 导出 cookies.txt

5. 保存文件，在程序中选择该文件

### Firefox
1. 安装 "Get cookies.txt" 扩展
   - Firefox 附加组件搜索: "Get cookies.txt"

2. 后续步骤同 Chrome

## 方法2: 使用浏览器开发者工具

### Chrome/Edge
1. 打开 https://youtube.com 并登录

2. 按 F12 打开开发者工具

3. 切换到 "Application" 或 "应用程序" 标签

4. 左侧找到 "Cookies" -> "https://www.youtube.com"

5. 使用以下脚本在控制台导出:
```javascript
document.cookie.split(';').forEach(c => {
    let [name, value] = c.trim().split('=');
    console.log(`${name}\t${value}`);
});
```

## 使用cookies.txt文件

运行程序时选择对应选项:
```
方式2: 使用cookies.txt文件
  X   - 使用cookies.txt文件
```

然后输入cookies.txt文件的路径，或直接拖拽文件到命令行窗口。

## 注意事项

- cookies会过期，如果下载失败请重新导出
- 确保在youtube.com已登录
- 导出后不要退出登录
