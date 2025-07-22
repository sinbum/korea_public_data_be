"""
Request/Response Transformation Layer - standardizes data formats across different sources.

Provides transformation capabilities for requests and responses to ensure
consistent data formats and structures across different public data APIs.
"""

import json
from typing import Dict, List, Optional, Any, Union, Callable, Type
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum
import logging

from .gateway import APIRequest, APIResponse

logger = logging.getLogger(__name__)


class TransformationType(str, Enum):
    """Types of transformations"""
    REQUEST = "request"
    RESPONSE = "response"
    DATA = "data"
    SCHEMA = "schema"


class TransformationRule(dict):
    """Transformation rule definition"""
    
    def __init__(
        self,
        source_path: str,
        target_path: str,
        transform_func: Optional[Callable] = None,
        default_value: Any = None,
        required: bool = False
    ):
        super().__init__()
        self["source_path"] = source_path
        self["target_path"] = target_path
        self["transform_func"] = transform_func
        self["default_value"] = default_value
        self["required"] = required


class DataTransformer(ABC):
    """Base class for data transformers"""
    
    @abstractmethod
    async def transform(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """Transform data"""
        pass
    
    @abstractmethod
    def get_transformation_type(self) -> TransformationType:
        """Get the type of transformation this transformer handles"""
        pass


class FieldMapper:
    """Maps fields between different data structures"""
    
    def __init__(self):
        self._mappings: Dict[str, TransformationRule] = {}
        self._custom_transformers: Dict[str, Callable] = {}
    
    def add_mapping(
        self,
        source_path: str,
        target_path: str,
        transform_func: Optional[Callable] = None,
        default_value: Any = None,
        required: bool = False
    ):
        """
        Add a field mapping rule.
        
        Args:
            source_path: Source field path (dot notation)
            target_path: Target field path (dot notation)
            transform_func: Optional transformation function
            default_value: Default value if source is missing
            required: Whether the field is required
        """
        rule = TransformationRule(
            source_path=source_path,
            target_path=target_path,
            transform_func=transform_func,
            default_value=default_value,
            required=required
        )
        self._mappings[source_path] = rule
    
    def add_custom_transformer(self, name: str, func: Callable):
        """Add a custom transformation function"""
        self._custom_transformers[name] = func
    
    def transform(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform data using defined mappings.
        
        Args:
            source_data: Source data dictionary
            
        Returns:
            Transformed data dictionary
        """
        result = {}
        
        for source_path, rule in self._mappings.items():
            try:
                # Get source value
                source_value = self._get_nested_value(source_data, source_path)
                
                if source_value is None:
                    if rule["required"]:
                        raise ValueError(f"Required field missing: {source_path}")
                    source_value = rule["default_value"]
                
                # Apply transformation function if provided
                if rule["transform_func"]:
                    source_value = rule["transform_func"](source_value)
                
                # Set target value
                if source_value is not None:
                    self._set_nested_value(result, rule["target_path"], source_value)
                    
            except Exception as e:
                logger.error(f"Error transforming field {source_path}: {e}")
                if rule["required"]:
                    raise
        
        return result
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any):
        """Set value in nested dictionary using dot notation"""
        keys = path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value


class RequestTransformer(DataTransformer):
    """Transforms API requests to standardized format"""
    
    def __init__(self):
        self._data_source_mappers: Dict[str, FieldMapper] = {}
        self._global_transformers: List[Callable] = []
    
    def get_transformation_type(self) -> TransformationType:
        return TransformationType.REQUEST
    
    def add_data_source_mapper(self, data_source: str, mapper: FieldMapper):
        """
        Add field mapper for specific data source.
        
        Args:
            data_source: Data source name
            mapper: Field mapper instance
        """
        self._data_source_mappers[data_source] = mapper
    
    def add_global_transformer(self, transformer: Callable):
        """
        Add global request transformer.
        
        Args:
            transformer: Transformer function
        """
        self._global_transformers.append(transformer)
    
    async def transform(self, request: APIRequest, context: Optional[Dict[str, Any]] = None) -> APIRequest:
        """
        Transform API request.
        
        Args:
            request: Original API request
            context: Transformation context
            
        Returns:
            Transformed API request
        """
        try:
            # Apply global transformers
            for transformer in self._global_transformers:
                request = await self._apply_transformer(transformer, request, context)
            
            # Apply data source specific mapping
            if request.data_source and request.data_source in self._data_source_mappers:
                mapper = self._data_source_mappers[request.data_source]
                
                # Transform query parameters
                if request.query_params:
                    request.query_params = mapper.transform(request.query_params)
                
                # Transform request body if present
                if request.body and isinstance(request.body, dict):
                    request.body = mapper.transform(request.body)
            
            logger.debug(f"Transformed request {request.request_id}")
            return request
            
        except Exception as e:
            logger.error(f"Error transforming request {request.request_id}: {e}")
            raise
    
    async def _apply_transformer(
        self, 
        transformer: Callable, 
        request: APIRequest, 
        context: Optional[Dict[str, Any]]
    ) -> APIRequest:
        """Apply a transformer function"""
        import asyncio
        
        if asyncio.iscoroutinefunction(transformer):
            return await transformer(request, context)
        else:
            return transformer(request, context)


class ResponseTransformer(DataTransformer):
    """Transforms API responses to standardized format"""
    
    def __init__(self):
        self._data_source_mappers: Dict[str, FieldMapper] = {}
        self._global_transformers: List[Callable] = []
        self._format_converters: Dict[str, Callable] = {}
    
    def get_transformation_type(self) -> TransformationType:
        return TransformationType.RESPONSE
    
    def add_data_source_mapper(self, data_source: str, mapper: FieldMapper):
        """
        Add field mapper for specific data source.
        
        Args:
            data_source: Data source name
            mapper: Field mapper instance
        """
        self._data_source_mappers[data_source] = mapper
    
    def add_global_transformer(self, transformer: Callable):
        """
        Add global response transformer.
        
        Args:
            transformer: Transformer function
        """
        self._global_transformers.append(transformer)
    
    def add_format_converter(self, format_name: str, converter: Callable):
        """
        Add format converter for specific data formats.
        
        Args:
            format_name: Format name (e.g., 'xml', 'csv')
            converter: Converter function
        """
        self._format_converters[format_name] = converter
    
    async def transform(self, response: APIResponse, context: Optional[Dict[str, Any]] = None) -> APIResponse:
        """
        Transform API response.
        
        Args:
            response: Original API response
            context: Transformation context
            
        Returns:
            Transformed API response
        """
        try:
            # Apply format conversion if needed
            if context and "input_format" in context:
                input_format = context["input_format"]
                if input_format in self._format_converters:
                    converter = self._format_converters[input_format]
                    response.data = await self._apply_converter(converter, response.data, context)
            
            # Apply global transformers
            for transformer in self._global_transformers:
                response = await self._apply_transformer(transformer, response, context)
            
            # Apply data source specific mapping
            if response.data_source and response.data_source in self._data_source_mappers:
                mapper = self._data_source_mappers[response.data_source]
                
                # Transform response data
                if response.data and isinstance(response.data, dict):
                    response.data = mapper.transform(response.data)
                elif response.data and isinstance(response.data, list):
                    # Transform each item in list
                    transformed_items = []
                    for item in response.data:
                        if isinstance(item, dict):
                            transformed_items.append(mapper.transform(item))
                        else:
                            transformed_items.append(item)
                    response.data = transformed_items
            
            logger.debug(f"Transformed response {response.response_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error transforming response {response.response_id}: {e}")
            raise
    
    async def _apply_transformer(
        self, 
        transformer: Callable, 
        response: APIResponse, 
        context: Optional[Dict[str, Any]]
    ) -> APIResponse:
        """Apply a transformer function"""
        import asyncio
        
        if asyncio.iscoroutinefunction(transformer):
            return await transformer(response, context)
        else:
            return transformer(response, context)
    
    async def _apply_converter(
        self, 
        converter: Callable, 
        data: Any, 
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Apply a format converter"""
        import asyncio
        
        if asyncio.iscoroutinefunction(converter):
            return await converter(data, context)
        else:
            return converter(data, context)


class StandardDataTransformer(DataTransformer):
    """Standard data transformations for common use cases"""
    
    def get_transformation_type(self) -> TransformationType:
        return TransformationType.DATA
    
    async def transform(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """Apply standard transformations"""
        if isinstance(data, dict):
            return await self._transform_dict(data, context)
        elif isinstance(data, list):
            return await self._transform_list(data, context)
        else:
            return data
    
    async def _transform_dict(self, data: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform dictionary data"""
        result = {}
        
        for key, value in data.items():
            # Standardize key naming (camelCase to snake_case)
            new_key = self._camel_to_snake(key)
            
            # Transform value recursively
            if isinstance(value, (dict, list)):
                result[new_key] = await self.transform(value, context)
            else:
                result[new_key] = self._transform_value(value)
        
        return result
    
    async def _transform_list(self, data: List[Any], context: Optional[Dict[str, Any]]) -> List[Any]:
        """Transform list data"""
        result = []
        
        for item in data:
            if isinstance(item, (dict, list)):
                result.append(await self.transform(item, context))
            else:
                result.append(self._transform_value(item))
        
        return result
    
    def _transform_value(self, value: Any) -> Any:
        """Transform individual values"""
        # Convert string dates to datetime objects
        if isinstance(value, str):
            # Try to parse as ISO date
            try:
                if 'T' in value and ('Z' in value or '+' in value):
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                pass
            
            # Convert string numbers
            if value.isdigit():
                return int(value)
            
            try:
                return float(value)
            except ValueError:
                pass
        
        return value
    
    def _camel_to_snake(self, name: str) -> str:
        """Convert camelCase to snake_case"""
        import re
        
        # Insert underscore before uppercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class XMLToJSONTransformer(DataTransformer):
    """Transforms XML data to JSON format"""
    
    def get_transformation_type(self) -> TransformationType:
        return TransformationType.DATA
    
    async def transform(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """Transform XML string to JSON"""
        if not isinstance(data, str):
            return data
        
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(data)
            return self._element_to_dict(root)
            
        except Exception as e:
            logger.error(f"Error converting XML to JSON: {e}")
            return data
    
    def _element_to_dict(self, element) -> Dict[str, Any]:
        """Convert XML element to dictionary"""
        result = {}
        
        # Add attributes
        if element.attrib:
            result.update(element.attrib)
        
        # Add text content
        if element.text and element.text.strip():
            if len(element) == 0:  # Leaf node
                return element.text.strip()
            else:
                result['_text'] = element.text.strip()
        
        # Add child elements
        for child in element:
            child_data = self._element_to_dict(child)
            
            if child.tag in result:
                # Convert to list if multiple elements with same tag
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result


class CSVToJSONTransformer(DataTransformer):
    """Transforms CSV data to JSON format"""
    
    def get_transformation_type(self) -> TransformationType:
        return TransformationType.DATA
    
    async def transform(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """Transform CSV string to JSON"""
        if not isinstance(data, str):
            return data
        
        try:
            import csv
            import io
            
            # Parse CSV
            csv_reader = csv.DictReader(io.StringIO(data))
            rows = []
            
            for row in csv_reader:
                # Convert values to appropriate types
                converted_row = {}
                for key, value in row.items():
                    converted_row[key] = self._convert_csv_value(value)
                rows.append(converted_row)
            
            return rows
            
        except Exception as e:
            logger.error(f"Error converting CSV to JSON: {e}")
            return data
    
    def _convert_csv_value(self, value: str) -> Any:
        """Convert CSV string value to appropriate type"""
        if not value:
            return None
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Try boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        return value


class TransformationManager:
    """Manages multiple transformers and transformation pipelines"""
    
    def __init__(self):
        self._transformers: Dict[str, DataTransformer] = {}
        self._pipelines: Dict[str, List[str]] = {}
    
    def register_transformer(self, name: str, transformer: DataTransformer):
        """
        Register a transformer.
        
        Args:
            name: Transformer name
            transformer: Transformer instance
        """
        self._transformers[name] = transformer
        logger.info(f"Registered transformer: {name}")
    
    def create_pipeline(self, name: str, transformer_names: List[str]):
        """
        Create a transformation pipeline.
        
        Args:
            name: Pipeline name
            transformer_names: List of transformer names in order
        """
        # Validate transformers exist
        for transformer_name in transformer_names:
            if transformer_name not in self._transformers:
                raise ValueError(f"Transformer not found: {transformer_name}")
        
        self._pipelines[name] = transformer_names
        logger.info(f"Created transformation pipeline: {name}")
    
    async def apply_pipeline(
        self, 
        pipeline_name: str, 
        data: Any, 
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Apply transformation pipeline to data.
        
        Args:
            pipeline_name: Pipeline name
            data: Data to transform
            context: Transformation context
            
        Returns:
            Transformed data
        """
        if pipeline_name not in self._pipelines:
            raise ValueError(f"Pipeline not found: {pipeline_name}")
        
        current_data = data
        transformer_names = self._pipelines[pipeline_name]
        
        for transformer_name in transformer_names:
            transformer = self._transformers[transformer_name]
            current_data = await transformer.transform(current_data, context)
        
        return current_data
    
    def get_transformer(self, name: str) -> Optional[DataTransformer]:
        """Get transformer by name"""
        return self._transformers.get(name)
    
    def list_transformers(self) -> List[str]:
        """List all registered transformers"""
        return list(self._transformers.keys())
    
    def list_pipelines(self) -> List[str]:
        """List all created pipelines"""
        return list(self._pipelines.keys())


# Pre-configured transformers
def create_standard_transformers() -> TransformationManager:
    """Create transformation manager with standard transformers"""
    manager = TransformationManager()
    
    # Register standard transformers
    manager.register_transformer("standard", StandardDataTransformer())
    manager.register_transformer("xml_to_json", XMLToJSONTransformer())
    manager.register_transformer("csv_to_json", CSVToJSONTransformer())
    
    # Create common pipelines
    manager.create_pipeline("normalize", ["standard"])
    manager.create_pipeline("xml_normalize", ["xml_to_json", "standard"])
    manager.create_pipeline("csv_normalize", ["csv_to_json", "standard"])
    
    return manager


# Global transformation manager
_transformation_manager: Optional[TransformationManager] = None


def get_transformation_manager() -> TransformationManager:
    """Get the global transformation manager instance"""
    global _transformation_manager
    if _transformation_manager is None:
        _transformation_manager = create_standard_transformers()
    return _transformation_manager