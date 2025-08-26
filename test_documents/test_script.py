#!/usr/bin/env python3
"""
测试Python文件
用于验证代码文件解析功能
"""

class TestClass:
    """测试类"""
    
    def __init__(self, name):
        self.name = name
    
    def test_method(self):
        """测试方法"""
        print(f"Hello, {self.name}!")
        return True

def main():
    """主函数"""
    test = TestClass("World")
    test.test_method()

if __name__ == "__main__":
    main()
