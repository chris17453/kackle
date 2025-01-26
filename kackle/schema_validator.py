import json
import yaml
import os
from typing import Dict, List, Any, Tuple

class SchemaValidator:
    def __init__(self, prompts_dir: str = 'prompts', schema_dir: str = 'prompt_validator'):
        self.prompts_dir = prompts_dir
        self.schema_dir = schema_dir
        
    def load_schema(self, prompt_name: str) -> Dict:
        base_name = os.path.splitext(prompt_name)[0]
        
        # Try JSON schema
        json_path = os.path.join(self.schema_dir, f"{base_name}.schema.json")
        if os.path.exists(json_path):
            with open(json_path) as f:
                return json.load(f)
                
        # Try YAML schema
        yaml_path = os.path.join(self.schema_dir, f"{base_name}.schema.yaml")
        if os.path.exists(yaml_path):
            with open(yaml_path) as f:
                return yaml.safe_load(f)
                
        raise FileNotFoundError(f"No schema found for {prompt_name}")

    def _validate_types(self, item: Dict, properties: Dict, issues: Dict):
        for field, value in item.items():
            if field in properties:
                field_schema = properties[field]
                if not self._validate_field(value, field_schema):
                    issues["invalid_types"].append(f"{field}: expected {field_schema['type']}")
        try:
            parts = date_str.split("-")
            return (len(parts) == 3 and 
                   len(parts[0]) == 4 and 
                   len(parts[1]) == 2 and 
                   len(parts[2]) == 2)
        except:
             return False
             
    def _validate_field(self, value: Any, schema: Dict) -> bool:
        expected_type = schema["type"]
        
        type_checks = {
            "string": lambda x: isinstance(x, str),
            "array": lambda x: isinstance(x, list),
            "number": lambda x: isinstance(x, (int, float)),
            "integer": lambda x: isinstance(x, int),
            "object": lambda x: isinstance(x, dict),
            "boolean": lambda x: isinstance(x, bool)
        }
        
        return type_checks.get(expected_type, lambda x: True)(value)

    def validate(self, prompt_name: str, content: str) -> Tuple[bool, Dict[str, List[str]], Any]:
        schema = self.load_schema(prompt_name)
        try:
            data = json.loads(content) if isinstance(content, str) else content
            if not isinstance(data, list):
                return False, {"validation_errors": ["Root must be an array"]}, None

            issues = {
                "missing_fields": [],
                "extra_fields": [],
                "invalid_types": [],
                "validation_errors": []
            }
            
            item_schema = schema["items"]
            properties = item_schema.get("properties", {})
            required = item_schema.get("required", [])
            
            for item in data:
                if not isinstance(item, dict):
                    issues["validation_errors"].append("Array items must be objects")
                    continue
                    
                for field in required:
                    if field not in item:
                        issues["missing_fields"].append(field)

                for field in item:
                    if field not in properties:
                        issues["extra_fields"].append(field)

                self._validate_types(item, properties, issues)

            is_valid = all(len(v) == 0 for v in issues.values())
            return is_valid, {k: v for k, v in issues.items() if v}, data

        except json.JSONDecodeError:
            return False, {"errors": ["Invalid JSON content"]}, None