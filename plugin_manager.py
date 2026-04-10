import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Dict, Any, List
from plugin_base import MCPPlugin

logger = logging.getLogger(__name__)

class PluginManager:
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins: Dict[str, MCPPlugin] = {}
        self.load_plugins()
    
    def load_plugins(self):
        """Load all plugins from plugins directory"""
        self.plugins.clear()
        
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return
        
        for plugin_file in self.plugins_dir.glob("*.py"):
            if plugin_file.stem.startswith("_"):
                continue
            
            try:
                spec = importlib.util.spec_from_file_location(
                    plugin_file.stem,
                    plugin_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                for item_name in dir(module):
                    item = getattr(module, item_name)
                    if (inspect.isclass(item) and 
                        issubclass(item, MCPPlugin) and 
                        item is not MCPPlugin):
                        
                        plugin_instance = item()
                        plugin_name = plugin_instance.name
                        
                        # 🔥 Plugin Manager 주입 (tool_planner가 도구 목록 조회 가능)
                        if hasattr(plugin_instance, 'set_plugin_manager'):
                            plugin_instance.set_plugin_manager(self)
                        
                        self.plugins[plugin_name] = plugin_instance
                        logger.info(f"Loaded: {plugin_name} v{plugin_instance.version}")
            
            except Exception as e:
                logger.error(f"Failed to load {plugin_file.name}: {e}")
        
        logger.info(f"Total plugins loaded: {len(self.plugins)}")
    
    def reload_plugins(self):
        """Reload all plugins"""
        logger.info("Reloading plugins...")
        self.load_plugins()
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all available plugins as MCP tools"""
        return [
            {
                "name": plugin.name,
                "description": plugin.description,
                "inputSchema": plugin.input_schema
            }
            for plugin in self.plugins.values()
        ]
    
    async def execute_plugin(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a plugin by name"""
        if name not in self.plugins:
            return {
                "error": f"Tool '{name}' not found",
                "available_tools": list(self.plugins.keys())
            }
        
        plugin = self.plugins[name]
        
        try:
            result = await plugin.execute(arguments)
            return result
        except Exception as e:
            return {
                "error": f"Plugin execution failed: {str(e)}",
                "tool": name
            }