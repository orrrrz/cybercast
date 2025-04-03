import os
import json
import hashlib
import functools
import time
import logging
from typing import Callable, Dict, Any, Optional

class DiskCache:
    """
    基于磁盘的缓存系统，用于缓存LLM API调用结果
    """
    
    def __init__(self, cache_dir: str, 
                 expire_after: int = 86400, 
                 hash_function: Optional[Callable] = None):
        """
        初始化缓存系统
        
        参数:
            cache_dir: 缓存文件存储目录
            expire_after: 缓存过期时间（秒），默认为24小时
            hash_function: 自定义哈希函数，默认使用MD5
        """

        self.cache_dir = cache_dir
        self.expire_after = expire_after
        self.hash_function = hash_function or self._default_hash
        
        # 确保缓存目录存在
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def _default_hash(self, data: Dict[str, Any]) -> str:
        """默认哈希函数，使用MD5"""
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.md5(serialized.encode('utf-8')).hexdigest()[:8]
    
    def _get_cache_path(self, cache_group: str, key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, cache_group, f"{key}.json")
    
    def get(self, cache_group: str, key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存数据
        
        参数:
            key: 缓存键
            
        返回:
            缓存的数据或None（如果不存在或已过期）
        """
        cache_path = self._get_cache_path(cache_group, key)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # 检查是否过期
            timestamp = cached_data.get('timestamp', 0)
            if time.time() - timestamp > self.expire_after:
                # 缓存已过期，删除缓存文件
                os.remove(cache_path)
                return None
            
            return cached_data.get('data')
        except (json.JSONDecodeError, IOError):
            # 缓存文件损坏，删除
            if os.path.exists(cache_path):
                os.remove(cache_path)
            return None
    
    def set(self, cache_group: str, key: str, data: Dict[str, Any]) -> None:
        """
        设置缓存数据
        
        参数:
            key: 缓存键
            data: 要缓存的数据
        """
        cache_path = self._get_cache_path(cache_group, key)

        if not os.path.exists(os.path.dirname(cache_path)):
            os.makedirs(os.path.dirname(cache_path))
        
        cache_data = {
            'timestamp': time.time(),
            'data': data
        }
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False)
    
    def clear(self, cache_group: Optional[str] = None, key: Optional[str] = None) -> None:
        """
        清除缓存
        
        参数:
            key: 特定的缓存键，不指定则清除所有缓存
        """
        if key:
            cache_path = self._get_cache_path(cache_group, key)
            if os.path.exists(cache_path):
                os.remove(cache_path)
        else:
            # 清除所有缓存
            for filename in os.listdir(self.cache_dir):
                if cache_group and filename.startswith(cache_group):
                    os.remove(os.path.join(self.cache_dir, filename))
                elif not cache_group:
                    os.remove(os.path.join(self.cache_dir, filename))
    
    def cached(self, func: Callable = None, key_params: Optional[list] = None):
        """
        缓存装饰器
        
        参数:
            func: 被装饰的函数
            key_params: 用于生成缓存键的参数名列表，默认使用所有参数
            
        返回:
            装饰后的函数
        """
        def decorator(f):
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                # 获取类名（如果是类方法）
                class_name = args[0].__class__.__name__ if args and hasattr(args[0], '__class__') else None
                # if class_name:
                    # logger.info(f"Decorator called by class: {class_name}")
                
                # 构建用于生成缓存键的参数字典
                cache_params = {}
                
                # 获取函数签名
                import inspect
                sig = inspect.signature(f)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                all_params = dict(bound_args.arguments)
                # print(f"All Params:")
                # for k, v in all_params.items():
                #     print(f"Param: {k}, Value: {v}")

                if 'self' in all_params:
                    # 将类名添加到缓存参数中
                    cache_params['__class__'] = class_name
                    del all_params['self']
                
                # 如果指定了key_params，只使用这些参数来生成缓存键
                if key_params:
                    # print(f"Key Params: {key_params}")
                    for param in key_params:
                        if param in all_params:
                            # print(f"Param: {param}, Value: {all_params[param]}")
                            cache_params[param] = all_params[param]
                else:
                    cache_params = all_params
                
                # 移除不可哈希的参数（如函数或类实例）
                for k, v in list(cache_params.items()):
                    try:
                        json.dumps({k: v})
                    except (TypeError, OverflowError):
                        cache_params[k] = str(v)
                
                # 添加函数名，确保不同函数调用相同参数时缓存不冲突
                cache_params['__func__'] = f.__name__

                # logger.info(f"Disk Cache Key: {json.dumps(cache_params, indent=2)}")
                
                # 生成缓存键
                cache_key = self.hash_function(cache_params)

                cache_group = class_name if class_name else "all"
                
                # 尝试从缓存获取结果
                cached_result = self.get(cache_group, cache_key)
                if cached_result is not None:
                    # print(f"Cache hit for {f.__name__}!")
                    # logger.info(f"Cache hit for {json.dumps(cache_params, indent=2)}!")
                    logging.info(f"Cache hit for {class_name}.{f.__name__}. Key: {cache_key}")
                    return cached_result
                
                # 缓存未命中，执行函数
                # print(f"Cache miss for {f.__name__}, executing...")
                logging.info(f"Cache miss for {class_name}.{f.__name__}. Key: {cache_key}. Requesting...")
                result = f(*args, **kwargs)
                
                # 缓存结果
                try:
                    # 尝试将结果序列化，确保可以缓存
                    json.dumps(result)
                    self.set(cache_group, cache_key, result)
                    # print(f"Cached to {cache_key}")
                    logging.info(f"Cached to {cache_key}")
                except (TypeError, OverflowError):
                    # print(f"Warning: Result of {f.__name__} is not JSON serializable, not caching.")
                    logging.warning(f"Warning: Result of {f.__name__} is not JSON serializable, not caching.")
                
                return result
            
            return wrapper
        
        # 支持直接使用@cache.cached或@cache.cached(key_params=['param1'])
        if func is not None:
            return decorator(func)
        return decorator


# 用于LLM调用的缓存装饰器
def llm_disk_cache(cache_dir: str = ".llm_cache", expire_after: int = 86400 * 7):
    """
    创建一个专门用于LLM调用的缓存装饰器
    
    参数:
        cache_dir: 缓存目录
        expire_after: 缓存过期时间（秒），默认为7天
        
    返回:
        缓存装饰器实例
    """
    return DiskCache(cache_dir=cache_dir, expire_after=expire_after).cached

