## 概述

`challenge_math_expert.py` 实现了一个「数学专家智能体」：  
结合 LLM + 专用数学库（`sympy`）+ 规则逻辑，对各类数学问题进行**分析 → 选择解法 → 求解 / 验证 → 教学式解释**。

相较于简单的「直接问 LLM 数学题」，该智能体的特点是：
- 先用 LLM 对问题进行结构化分析，识别领域 / 变量 / 已知条件 / 子问题；
- 针对不同数学领域，调用不同的专用求解函数（如代数、几何、微积分）；
- 用 LLM 对求解结果进行二次验证与润色，生成教学型解释。

---

## 架构总览

### 1. 模型初始化

统一使用 ARK OpenAI 兼容接口：

```python
ARK_API_KEY = os.getenv("ARK_API_KEY")
ARK_MODEL = os.getenv("ARK_MODEL")
ARK_BASE_URL = os.getenv("ARK_BASE_URL")

llm = ChatOpenAI(
    model=ARK_MODEL,
    api_key=ARK_API_KEY,
    base_url=ARK_BASE_URL,
    temperature=0.1,
)
```

`MathExpertAgent` 内部通过 `self.llm = llm` 复用这一模型。

---

### 2. 核心类 `MathExpertAgent`

```python
class MathExpertAgent:
    def __init__(self):
        self.llm = llm
        self.supported_domains = [
            "代数", "几何", "微积分", "统计",
            "线性代数", "离散数学", "数论",
        ]
```

并提供一系列方法：
- `analyze_math_problem`：使用 LLM 对题目做结构化分析；
- `solve_algebra`：代数求解（基于 sympy）；
- `solve_geometry`：几何分析与部分数值计算；
- `solve_calculus`：微积分（求导 / 积分）；
- `general_math_solution`：通用 LLM 数学解题；
- `verify_solution`：校验方案正确性；
- `generate_explanation`：生成详细教学解释；
- `solve_step_by_step`：串起上述所有步骤的总控方法。

---

## 详细流程：`solve_step_by_step`

入口方法：

```python
def solve_step_by_step(self, problem: str) -> str:
    print("步骤1：分析问题")
    analysis = self.analyze_math_problem(problem)

    print("步骤2：选择解法")
    if "代数" in domain:
        solution = self.solve_algebra(problem, analysis)
    elif "几何" in domain:
        solution = self.solve_geometry(problem, analysis)
    elif "微积分" in domain or "导数" in problem or "积分" in problem:
        solution = self.solve_calculus(problem, analysis)
    else:
        solution = self.general_math_solution(problem, analysis)

    print("步骤3：验证结果")
    verified_solution = self.verify_solution(problem, solution, analysis)

    print("步骤4：生成详细解释")
    explanation = self.generate_explanation(problem, verified_solution, analysis)

    return explanation
```

整体步骤可以概括为：

1. **分析问题**：`analyze_math_problem`
2. **选择解法**：根据分析结果路由到不同领域求解函数
3. **验证结果**：`verify_solution`
4. **生成教学解释**：`generate_explanation`

---

## 步骤 1：问题分析 `analyze_math_problem`

```python
def analyze_math_problem(self, problem: str) -> Dict[str, Any]:
    analysis_prompt = f"""
    请分析以下数学问题：

    问题：{problem}

    请返回JSON格式的分析结果：
    {{
        "domain": "问题领域（从{self.supported_domains}中选择）",
        "complexity": "简单/中等/复杂",
        "variables": ["识别出的变量列表"],
        "known_info": ["已知条件"],
        "unknown_info": ["需要求解的未知数"],
        "solution_method": "建议的解决方法",
        "subproblems": ["分解出的子问题"]
    }}
    """

    response = self.llm.invoke(analysis_prompt)
    try:
        return json.loads(response.content)
    except:
        return {
            "domain": "未知",
            "complexity": "中等",
            "variables": [],
            "subproblems": [problem],
        }
```

**目的：**
- 把自然语言数学题转成结构化信息：
  - 领域（代数 / 几何 / 微积分 / …）
  - 复杂度
  - 变量、已知、未知
  - 可能的解法、子问题列表

**后续用途：**
- `domain` 决定走哪个求解分支；
- `subproblems` 等可用于更细粒度拆解（当前版本主要用于日志展示）。

---

## 步骤 2：按领域路由求解

在 `solve_step_by_step` 中：

```python
domain = analysis.get("domain", "").lower()

if "代数" in domain:
    solution = self.solve_algebra(problem, analysis)
elif "几何" in domain:
    solution = self.solve_geometry(problem, analysis)
elif "微积分" in domain or "导数" in domain or "积分" in domain:
    solution = self.solve_calculus(problem, analysis)
else:
    solution = self.general_math_solution(problem, analysis)
```

### 2.1 代数：`solve_algebra`

**目标：** 对包含方程的题目（如「解方程：2x + 5 = 13」）进行求解。

核心逻辑：

```python
equations = re.findall(r'([\w\s+\-*/^()=]+)', problem)

for eq in equations[:2]:
    if '=' in eq:
        left, right = eq.split('=', 1)
        x = sp.symbols('x')
        expr = sp.sympify(left + '-(' + right + ')')
        solution = sp.solve(expr, x)
        solutions.append(f"方程 {eq} 的解: {solution}")
```

说明：
- 使用正则粗略提取带 `=` 的表达式；
- 将 `left = right` 转化为 `left - (right) = 0`；
- 使用 `sympy.solve` 对未知数 `x` 求解；
- 若解析失败则返回「需要手动求解」提示。

### 2.2 几何：`solve_geometry`

**目标：** 从几何描述中提取图形与参数，并进行基础数值计算。

逻辑：
- 扫描题目中是否出现「圆 / 三角形 / 矩形 / 正方形 / 圆柱 / 球体」等关键字；
- 用正则提取题目内的所有数字；
- 针对常见场景直接计算：
  - 圆面积：`π r^2`
  - 矩形面积：`a × b`

输出示例：

```text
几何问题分析:
识别图形: 圆
提取数值: ['7']
圆面积 (r=7.0) = 153.94
```

### 2.3 微积分：`solve_calculus`

**目标：** 对含「导数」「微分」「积分」「∫」等关键词的题目做符号求解。

求导场景：

```python
func_match = re.search(r'[fF]\(x\)\s*=\s*([^,\n]+)', problem)
if func_match:
    func_str = func_match.group(1)
    x = sp.symbols('x')
    func = sp.sympify(func_str)
    derivative = sp.diff(func, x)
```

积分场景：

```python
int_match = re.search(r'∫[^∫]+dx', problem)
if int_match:
    int_expr = int_match.group(0).replace('∫', '').replace('dx', '')
    x = sp.symbols('x')
    expr = sp.sympify(int_expr)
    integral = sp.integrate(expr, x)
```

输出会包含原函数 / 积分表达式与计算结果。

### 2.4 通用 LLM 解题：`general_math_solution`

当领域不明确或不在特定分支覆盖范围内时，退回到 LLM 纯推理：

```python
prompt = f"""
请解决以下数学问题，并展示详细步骤：

问题：{problem}

分析结果：
{json.dumps(analysis, ensure_ascii=False, indent=2)}

请分步骤解答，并给出最终答案。
"""
response = self.llm.invoke(prompt)
return response.content
```

---

## 步骤 3：验证方案 `verify_solution`

```python
prompt = f"""
请验证以下数学问题的解决方案是否正确：

原问题：{problem}

建议的解决方案：
{solution}

请检查：
1. 计算过程是否正确
2. 单位是否一致
3. 答案是否合理

如果发现问题，请修正。
"""

response = self.llm.invoke(prompt)
return response.content
```

**作用：**
- 把「求解过程 + 答案」交给 LLM 做一次复核；
- 要求模型指出计算 / 单位 / 结果合理性问题并自动修正。

返回内容会被视为「已验证 / 修正后的方案」，传给下一个步骤使用。

---

## 步骤 4：生成教学解释 `generate_explanation`

```python
prompt = f"""
请为以下数学问题的解决方案生成详细的教学解释：

问题：{problem}

解决方案：
{solution}

请包括：
1. 关键概念解释
2. 每一步的原理
3. 易错点提醒
4. 类似问题的解法
"""
response = self.llm.invoke(prompt)
return response.content
```

**目标：** 面向学习者输出「带讲解的解答」，而不仅仅是结果：
- 解释用了哪些数学概念（如函数、导数、勾股定理等）；
- 每步推导基于什么公式或定理；
- 常见错误点有哪些；
- 同类题一般如何思考和求解。

这一步的输出就是 `solve_step_by_step` 的最终返回结果。

---

## 流程图

```mermaid
graph TD
    Start([开始]) --> Input[输入数学题目 problem]

    Input --> Analyze[步骤1：analyze_math_problem<br/>LLM 结构化分析]
    Analyze --> Domain{根据 analysis.domain<br/>与题目关键词}

    Domain -->|包含 "代数"| Algebra[solve_algebra<br/>Sympy 解方程]
    Domain -->|包含 "几何"| Geometry[solve_geometry<br/>几何分析与数值计算]
    Domain -->|包含 "微积分" / "导数" / "积分"| Calculus[solve_calculus<br/>求导 / 积分]
    Domain -->|其他| General[general_math_solution<br/>LLM 通用解题]

    Algebra --> Sol[得到初步解答 solution]
    Geometry --> Sol
    Calculus --> Sol
    General --> Sol

    Sol --> Verify[步骤3：verify_solution<br/>LLM 验证与修正]
    Verify --> Explain[步骤4：generate_explanation<br/>生成教学解释]
    Explain --> End([返回最终教学式解答])

    style Start fill:#e1f5ff
    style Input fill:#fff4e1
    style Analyze fill:#ffe1f5
    style Domain fill:#e1ffe1
    style Algebra fill:#f0e1ff
    style Geometry fill:#f0e1ff
    style Calculus fill:#f0e1ff
    style General fill:#f0e1ff
    style Verify fill:#ffe1e1
    style Explain fill:#e1ffe1
    style End fill:#e1f5ff
```

---

## 与其他模块的关系

- 与 `challenge_multi_tool.py`：  
  - 可作为另一个「专用数学工具节点」被嵌入多工具工作流中；  
  - 例如，路由层先判断「这是复杂数学题」，则调用 `MathExpertAgent.solve_step_by_step` 作为子流程。

- 与 `challenge_memory.py`：  
  - 可以在分析与解题时参考用户历史偏好（如「喜欢详细解释」「需要更多例题」）；  
  - 或将用户的薄弱知识点写回记忆，后续题目中给出更多针对性提示。

---

## 使用方式

### 1. 环境准备

```bash
pip install sympy numpy "langchain>=0.3" langchain-openai

export ARK_API_KEY="your-api-key"
export ARK_MODEL="your-model-name"
export ARK_BASE_URL="https://your-ark-endpoint"
```

### 2. 运行内置测试

```bash
cd neural-upgrade/langchain/code-demo
python challenge_math_expert.py
```

脚本会：
- 尝试运行 `challenge_multi_tool` 的多工具测试（若导入失败会跳过）；
- 依次对 5 个预设数学问题调用 `solve_step_by_step`，并打印完整过程与最终解答。

---

## 总结

`challenge_math_expert.py` 展示了一个「领域专家型 Agent」的基本结构：
- 先做结构化分析，再按领域路由到不同工具和算法；
- 将传统数学库（Sympy 等）与 LLM 推理结合；
- 最终输出人类友好的教学解释，而不仅是数值答案。

这套模式可以推广到其他领域（物理专家、财务专家等），只需替换领域分析提示词与专用求解模块即可。

