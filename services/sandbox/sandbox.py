
import sys
import io
import threading
import time
from typing import Dict, Any, Optional, Callable
from contextlib import redirect_stdout, redirect_stderr

from .security_check import SecurityChecker
from .error_helper import ErrorHelper


class TimeoutException(Exception):
    """超时异常 - 当代码执行超过指定时间时抛出"""
    pass


class Sandbox:

    def __init__(self, timeout: int = 10):
        """
        初始化沙箱
        
        参数:
            timeout: 执行超时时间，单位秒（默认10秒）
        """
        self.timeout = timeout  # 超时时间
        self.security_checker = SecurityChecker()  # 安全检查器
        self.error_helper = ErrorHelper()  # 错误处理助手
        
        # 创建受限制的全局命名空间
        self.safe_globals = self._create_safe_globals()
    
    def _create_safe_globals(self) -> Dict:

        safe_builtins = {}
        
        # 安全的内置函数白名单
        # 这些函数不会对系统造成危害
        allowed_builtins = [
            'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
            'callable', 'chr', 'classmethod', 'complex', 'dict', 'dir', 'divmod',
            'enumerate', 'filter', 'float', 'format', 'frozenset', 'getattr',
            'hasattr', 'hash', 'help', 'hex', 'id', 'int', 'isinstance', 'issubclass',
            'iter', 'len', 'list', 'locals', 'map', 'max', 'min', 'next', 'object',
            'oct', 'ord', 'pow', 'print', 'property', 'range', 'repr', 'reversed',
            'round', 'set', 'slice', 'sorted', 'staticmethod', 'str', 'sum', 'super',
            'tuple', 'type', 'zip', '__import__',
        ]
        
        # 构建安全的内置函数字典
        import builtins
        for name in allowed_builtins:
            if hasattr(builtins, name):
                safe_builtins[name] = getattr(builtins, name)
        
        # 重载危险函数，替换为安全版本
        safe_builtins['__import__'] = self._safe_import
        safe_builtins['open'] = self._safe_open
        
        return {
            '__builtins__': safe_builtins,  # 安全的内置函数
            '__name__': '__sandbox__',      # 模块名
            '__doc__': None,                # 文档
        }
    
    def _safe_import(self, name, *args, **kwargs):

        from .security_check import DANGEROUS_MODULES, ALLOWED_MODULES
        
        # 获取模块名的第一部分（如 'os.path' -> 'os'）
        module_name = name.split('.')[0]
        
        # 检查是否是危险模块
        if module_name in DANGEROUS_MODULES:
            raise ImportError(f'禁止导入模块: {name}')
        
        # 检查是否在白名单中
        if module_name not in ALLOWED_MODULES:
            raise ImportError(f'不允许导入模块: {name}')
        
        # 真正的导入
        import importlib
        return importlib.__import__(name, *args, **kwargs)
    
    def _safe_open(self, *args, **kwargs):

        raise PermissionError('禁止文件读写操作')
    
    def execute(self, code: str) -> Dict[str, Any]:

        result = {
            'success': False,
            'output': '',
            'errors': [],
            'execution_time': 0,
        }
        
        # 1. 安全检查
        is_safe, security_errors = self.security_checker.check_code(code)
        result['errors'].extend(security_errors)
        
        if not is_safe:
            result['output'] = '⚠️ 发现安全问题，请检查代码后重试\n'
            return result
        
        # 2. 执行代码
        stdout_capture = io.StringIO()  # 捕获标准输出
        stderr_capture = io.StringIO()  # 捕获标准错误
        start_time = time.time()        # 记录开始时间
        
        try:
            # 重定向输出到捕获器
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                self._execute_with_timeout(code)  # 执行代码（带超时）
            
            # 执行成功
            result['success'] = True
            result['output'] = stdout_capture.getvalue()
            
        except TimeoutException:
            # 执行超时
            result['errors'].append({
                'type': '超时警告',
                'line': None,
                'column': None,
                'message': f'代码执行超过 {self.timeout} 秒，已自动终止',
                'suggestion': '检查是否有死循环或无限递归，或者优化代码逻辑'
            })
            result['output'] = stdout_capture.getvalue()
            
        except Exception as e:
            # 其他运行时错误
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_info = self.error_helper.format_error(
                exc_type, exc_value, exc_traceback
            )
            
            result['errors'].append({
                'type': error_info['type'],
                'line': error_info['line'],
                'column': error_info['column'],
                'message': error_info['friendly_message'],
                'suggestion': '\n'.join(error_info['suggestions'])
            })
            
            result['output'] = stdout_capture.getvalue()
            if stderr_capture.getvalue():
                result['output'] += '\n' + stderr_capture.getvalue()
        
        finally:
            # 计算执行时间（无论成功失败都执行）
            result['execution_time'] = round(time.time() - start_time, 3)
        
        return result
    
    def _execute_with_timeout(self, code: str):

        result = {'exception': None}
        
        # 在新线程中执行代码的目标函数
        def target():
            try:
                # exec 在受限的命名空间中执行代码
                exec(code, self.safe_globals, {})
            except Exception as e:
                result['exception'] = e
        
        # 创建并启动线程
        thread = threading.Thread(target=target)
        thread.daemon = True  # 设置为守护线程，主程序退出时线程也退出
        thread.start()
        thread.join(self.timeout)  # 等待线程结束（最多等待 timeout 秒）
        
        # 检查线程是否还在运行（超时）
        if thread.is_alive():
            raise TimeoutException(f'执行超过 {self.timeout} 秒')
        
        # 检查是否有异常
        if result['exception']:
            raise result['exception']


# 便捷函数 - 外部使用的接口
def run_code(code: str, timeout: int = 10) -> Dict[str, Any]:

    sandbox = Sandbox(timeout=timeout)
    return sandbox.execute(code)


if __name__ == '__main__':
    test_code = '''print('Hello, 沙箱测试!')'''
    result = run_code(test_code)
    print(result)
