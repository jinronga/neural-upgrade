# 数学专家智能体
import os
import json
import sympy as sp
import numpy as np
from typing import List, Dict, Any
import re
from langchain_openai import ChatOpenAI

ARK_API_KEY = os.getenv("ARK_API_KEY")
ARK_MODEL = os.getenv("ARK_MODEL")
ARK_BASE_URL = os.getenv("ARK_BASE_URL")

llm = ChatOpenAI(
    model=ARK_MODEL,
    api_key=ARK_API_KEY,
    base_url=ARK_BASE_URL,
    temperature=0.1,
)


class MathExpertAgent:
    """数学专家智能体"""
    
    def __init__(self):
        self.llm = llm  # 使用前面定义的LLM
        self.supported_domains = [
            "代数", "几何", "微积分", "统计", 
            "线性代数", "离散数学", "数论"
        ]
    
    def analyze_math_problem(self, problem: str) -> Dict[str, Any]:
        """分析数学问题，识别领域和复杂度"""
        
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
                "subproblems": [problem]
            }
    
    def solve_algebra(self, problem: str, analysis: Dict) -> str:
        """解代数问题"""
        try:
            # 使用sympy解方程
            # 提取方程
            equations = re.findall(r'([\w\s+\-*/^()=]+)', problem)
            
            solutions = []
            for eq in equations[:2]:  # 处理前两个方程
                if '=' in eq:
                    # 简化解方程过程
                    left, right = eq.split('=', 1)
                    
                    # 尝试解析为sympy表达式
                    try:
                        x = sp.symbols('x')
                        expr = sp.sympify(left + '-(' + right + ')')
                        solution = sp.solve(expr, x)
                        solutions.append(f"方程 {eq} 的解: {solution}")
                    except:
                        solutions.append(f"方程 {eq}: 需要手动求解")
            
            return "\n".join(solutions) if solutions else "未找到可解的方程"
            
        except Exception as e:
            return f"代数求解错误: {str(e)}"
    
    def solve_geometry(self, problem: str, analysis: Dict) -> str:
        """解几何问题"""
        # 提取几何元素
        shapes = []
        for shape in ["圆", "三角形", "矩形", "正方形", "圆柱", "球体"]:
            if shape in problem:
                shapes.append(shape)
        
        # 提取数值
        numbers = re.findall(r'\d+\.?\d*', problem)
        
        result = f"几何问题分析:\n"
        result += f"识别图形: {', '.join(shapes) if shapes else '未知图形'}\n"
        result += f"提取数值: {numbers}\n"
        
        # 简单计算
        if "面积" in problem:
            if "圆" in shapes and len(numbers) >= 1:
                r = float(numbers[0])
                area = 3.14159 * r * r
                result += f"圆面积 (r={r}) = {area:.2f}\n"
            elif "矩形" in shapes and len(numbers) >= 2:
                a, b = map(float, numbers[:2])
                result += f"矩形面积 ({a}×{b}) = {a*b:.2f}\n"
        
        return result
    
    def solve_calculus(self, problem: str, analysis: Dict) -> str:
        """解微积分问题"""
        result = "微积分求解:\n"
        
        try:
            # 尝试求导
            if "导数" in problem or "微分" in problem:
                # 提取函数表达式
                func_match = re.search(r'[fF]\(x\)\s*=\s*([^,\n]+)', problem)
                if func_match:
                    func_str = func_match.group(1)
                    x = sp.symbols('x')
                    func = sp.sympify(func_str)
                    derivative = sp.diff(func, x)
                    result += f"函数 f(x) = {func_str}\n"
                    result += f"导数 f'(x) = {derivative}\n"
            
            # 尝试积分
            elif "积分" in problem or "∫" in problem:
                int_match = re.search(r'∫[^∫]+dx', problem)
                if int_match:
                    int_expr = int_match.group(0).replace('∫', '').replace('dx', '')
                    x = sp.symbols('x')
                    expr = sp.sympify(int_expr)
                    integral = sp.integrate(expr, x)
                    result += f"积分 ∫({int_expr})dx = {integral} + C\n"
        
        except Exception as e:
            result += f"计算错误: {str(e)}\n"
        
        return result
    
    def solve_step_by_step(self, problem: str) -> str:
        """分步解决数学问题"""
        
        print(f"\n{'='*60}")
        print(f"数学专家处理: {problem}")
        print('='*60)
        
        # 1. 分析问题
        print("\n[步骤1] 分析问题...")
        analysis = self.analyze_math_problem(problem)
        print(f"   领域: {analysis.get('domain')}")
        print(f"   复杂度: {analysis.get('complexity')}")
        print(f"   子问题: {analysis.get('subproblems', [])}")
        
        # 2. 根据领域选择解法
        domain = analysis.get("domain", "").lower()
        solution = ""
        
        print(f"\n[步骤2] 选择解法...")
        if "代数" in domain:
            print("   使用代数求解器")
            solution = self.solve_algebra(problem, analysis)
        elif "几何" in domain:
            print("   使用几何求解器")
            solution = self.solve_geometry(problem, analysis)
        elif "微积分" in domain or "导数" in domain or "积分" in domain:
            print("   使用微积分求解器")
            solution = self.solve_calculus(problem, analysis)
        else:
            print("   使用通用数学推理")
            solution = self.general_math_solution(problem, analysis)
        
        # 3. 验证结果
        print(f"\n[步骤3] 验证结果...")
        verified_solution = self.verify_solution(problem, solution, analysis)
        
        # 4. 生成解释
        print(f"\n[步骤4] 生成详细解释...")
        explanation = self.generate_explanation(problem, verified_solution, analysis)
        
        return explanation
    
    def general_math_solution(self, problem: str, analysis: Dict) -> str:
        """通用数学解法"""
        prompt = f"""
        请解决以下数学问题，并展示详细步骤：
        
        问题：{problem}
        
        分析结果：
        {json.dumps(analysis, ensure_ascii=False, indent=2)}
        
        请分步骤解答，并给出最终答案。
        """
        
        response = self.llm.invoke(prompt)
        return response.content
    
    def verify_solution(self, problem: str, solution: str, analysis: Dict) -> str:
        """验证解决方案"""
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
    
    def generate_explanation(self, problem: str, solution: str, analysis: Dict) -> str:
        """生成详细解释"""
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

# 测试数学专家
def test_math_expert():
    """测试数学专家智能体"""
    
    math_expert = MathExpertAgent()
    
    test_problems = [
        "解方程：2x + 5 = 13",
        "一个圆的半径是7厘米，求它的面积和周长",
        "求函数 f(x) = x² + 3x - 4 的导数",
        "计算从1到100所有整数的和",
        "一个直角三角形，两条直角边分别是3和4，求斜边的长度"
    ]
    
    for i, problem in enumerate(test_problems, 1):
        print(f"\n{'#'*60}")
        print(f"数学问题 {i}: {problem}")
        print('#'*60)
        
        solution = math_expert.solve_step_by_step(problem)
        print(f"\n最终解答:\n{solution}")
        print("="*60)

if __name__ == "__main__":
    # 运行测试
    print("测试多工具调用:")
    try:
        # 与 challenge_multi_tool.py 同目录时可直接导入
        from challenge_multi_tool import test_multi_tool

        test_multi_tool()
    except Exception as e:
        print(f"跳过多工具测试（导入或执行失败）: {e}")
    
    print("\n\n测试数学专家:")
    test_math_expert()