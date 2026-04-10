from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class MCPPlugin(ABC):
    """
    MCP 플러그인 베이스 클래스
    
    모든 플러그인은 이 클래스를 상속받아야 합니다.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """플러그인 이름 (도구 이름)"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """플러그인 설명"""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """입력 스키마 (JSON Schema)"""
        pass
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        플러그인 실행
        
        Args:
            arguments: 도구 호출 인자
            
        Returns:
            실행 결과
        """
        pass
    
    @property
    def enabled(self) -> bool:
        """플러그인 활성화 여부 (기본: True)"""
        return True
    
    @property
    def version(self) -> str:
        """플러그인 버전"""
        return "1.0.0"
    
    @property
    def author(self) -> str:
        """플러그인 작성자"""
        return "Unknown"
    
    def to_tool_definition(self) -> Dict[str, Any]:
        """MCP 도구 정의로 변환"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }