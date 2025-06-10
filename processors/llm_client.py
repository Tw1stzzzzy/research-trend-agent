import yaml
import requests
from openai import OpenAI

class LLMClient:
    """统一的LLM客户端，支持多个免费API提供商"""
    
    def __init__(self):
        with open("configs/config.yaml", "r") as f:
            self.config = yaml.safe_load(f)
        self.provider = self.config.get('llm_provider', 'huggingface')
        
    def generate_response(self, messages, temperature=0.3, max_tokens=500):
        """
        统一的响应生成接口
        messages: [{"role": "system/user", "content": "..."}]
        """
        if self.provider == "huggingface":
            return self._call_huggingface(messages, temperature, max_tokens)
        elif self.provider == "groq":
            return self._call_groq(messages, temperature, max_tokens)
        elif self.provider == "together":
            return self._call_together(messages, temperature, max_tokens)
        elif self.provider == "openai":
            return self._call_openai(messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _call_huggingface(self, messages, temperature, max_tokens):
        """调用Hugging Face Inference API"""
        api_key = self.config['huggingface']['api_key']
        model = self.config['huggingface']['model']
        
        # 将messages转换为单个prompt
        prompt = self._messages_to_prompt(messages)
        
        headers = {"Authorization": f"Bearer {api_key}"}
        data = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "return_full_text": False
            }
        }
        
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('generated_text', '').strip()
            return result.get('generated_text', '').strip()
        else:
            raise Exception(f"Hugging Face API error: {response.status_code} {response.text}")
    
    def _call_groq(self, messages, temperature, max_tokens):
        """调用Groq API"""
        api_key = self.config['groq']['api_key']
        model = self.config['groq']['model']
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content.strip()
    
    def _call_together(self, messages, temperature, max_tokens):
        """调用Together AI API"""
        api_key = self.config['together']['api_key']
        model = self.config['together']['model']
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.together.xyz"
        )
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content.strip()
    
    def _call_openai(self, messages, temperature, max_tokens):
        """调用OpenAI API"""
        api_key = self.config['openai']['api_key']
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 使用更便宜的模型
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content.strip()
    
    def _messages_to_prompt(self, messages):
        """将OpenAI格式的messages转换为单个prompt（适用于HuggingFace）"""
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt += f"System: {content}\n"
            elif role == "user":
                prompt += f"Human: {content}\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n"
        prompt += "Assistant: "
        return prompt 