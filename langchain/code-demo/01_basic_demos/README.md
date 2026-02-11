# LangChain 示例代码

## 配置说明

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

或者手动安装：

```bash
pip install langchain-openai langchain-core
```

### 2. 配置环境变量

使用 `export` 命令设置环境变量：

```bash
export ARK_API_KEY="your-api-key"
export ARK_MODEL="ep-20260207222458-79vwd"  # 可选，有默认值
export ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"  # 可选，有默认值
```

**永久设置（推荐）：**

将环境变量添加到 `~/.zshrc` 或 `~/.bashrc` 文件中：

```bash
# 编辑配置文件
nano ~/.zshrc  # 或 vim ~/.zshrc

# 添加以下内容
export ARK_API_KEY="your-api-key"
export ARK_MODEL="ep-20260207222458-79vwd"
export ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"

# 保存后重新加载
source ~/.zshrc
```

### 3. 运行代码

```bash
python first-langchain.py
```

## 注意事项

- 必须设置 `ARK_API_KEY` 环境变量，否则程序会报错
- `ARK_MODEL` 和 `ARK_BASE_URL` 有默认值，可以不设置
- 环境变量只在当前终端会话有效，关闭终端后需要重新设置（除非写入配置文件）

