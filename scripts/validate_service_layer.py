#!/usr/bin/env python3
"""
Service Layer Validation Script

Validates the complete service layer implementation including:
- Interface compliance
- SOLID principles adherence
- Design pattern implementation
- Error handling
- Performance characteristics
"""

import asyncio
import inspect
import importlib
import sys
import os
from typing import Dict, List, Any, Optional, get_type_hints
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.shared.interfaces.base_service import BaseService
from app.shared.interfaces.domain_services import (
    IAnnouncementService, IBusinessService, IContentService, IStatisticsService
)
from app.shared.cqrs.commands import Command
from app.shared.cqrs.queries import Query
from app.shared.cqrs.bus import CommandBus, QueryBus
from app.shared.events.domain_events import DomainEvent, EventBus
from app.shared.events.event_store import EventStore, InMemoryEventStore
from app.shared.events.cross_domain_services import CrossDomainService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceLayerValidator:
    """Validates the service layer architecture and implementation."""
    
    def __init__(self):
        self.results = {
            'interface_compliance': [],
            'solid_principles': [],
            'design_patterns': [],
            'error_handling': [],
            'performance': [],
            'overall_score': 0
        }
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run complete service layer validation."""
        logger.info("Starting service layer validation...")
        
        # Run all validation checks
        await self._validate_interface_compliance()
        await self._validate_solid_principles()
        await self._validate_design_patterns()
        await self._validate_error_handling()
        await self._validate_performance()
        
        # Calculate overall score
        self._calculate_overall_score()
        
        logger.info("Service layer validation completed")
        return self.results
    
    async def _validate_interface_compliance(self):
        """Validate that services comply with their interfaces."""
        logger.info("Validating interface compliance...")
        
        checks = []
        
        # Check BaseService implementation
        try:
            from app.domains.announcements.service import AnnouncementService
            from app.domains.businesses.service import BusinessService
            from app.domains.contents.service import ContentService
            from app.domains.statistics.service import StatisticsService
            
            services = [
                ('AnnouncementService', AnnouncementService),
                ('BusinessService', BusinessService),
                ('ContentService', ContentService),
                ('StatisticsService', StatisticsService)
            ]
            
            for service_name, service_class in services:
                # Check if inherits from BaseService
                if issubclass(service_class, BaseService):
                    checks.append({
                        'check': f'{service_name} inherits from BaseService',
                        'status': 'PASS',
                        'details': 'Service properly inherits from base class'
                    })
                else:
                    checks.append({
                        'check': f'{service_name} inherits from BaseService',
                        'status': 'FAIL',
                        'details': 'Service does not inherit from BaseService'
                    })
                
                # Check abstract method implementations
                abstract_methods = self._get_abstract_methods(BaseService)
                implemented_methods = [method for method in dir(service_class) 
                                     if not method.startswith('_') and callable(getattr(service_class, method))]
                
                missing_methods = [method for method in abstract_methods 
                                 if method not in implemented_methods]
                
                if not missing_methods:
                    checks.append({
                        'check': f'{service_name} implements all abstract methods',
                        'status': 'PASS',
                        'details': 'All abstract methods implemented'
                    })
                else:
                    checks.append({
                        'check': f'{service_name} implements all abstract methods',
                        'status': 'FAIL',
                        'details': f'Missing methods: {missing_methods}'
                    })
                
                # Check domain interface compliance
                domain_interfaces = {
                    'AnnouncementService': IAnnouncementService,
                    'BusinessService': IBusinessService,
                    'ContentService': IContentService,
                    'StatisticsService': IStatisticsService
                }
                
                if service_name in domain_interfaces:
                    interface = domain_interfaces[service_name]
                    if self._implements_interface(service_class, interface):
                        checks.append({
                            'check': f'{service_name} implements domain interface',
                            'status': 'PASS',
                            'details': f'Implements {interface.__name__}'
                        })
                    else:
                        checks.append({
                            'check': f'{service_name} implements domain interface',
                            'status': 'FAIL',
                            'details': f'Does not implement {interface.__name__}'
                        })
        
        except ImportError as e:
            checks.append({
                'check': 'Service imports',
                'status': 'FAIL',
                'details': f'Import error: {e}'
            })
        
        self.results['interface_compliance'] = checks
    
    async def _validate_solid_principles(self):
        """Validate SOLID principles adherence."""
        logger.info("Validating SOLID principles...")
        
        checks = []
        
        # Single Responsibility Principle
        checks.extend(await self._check_single_responsibility())
        
        # Open/Closed Principle
        checks.extend(await self._check_open_closed())
        
        # Liskov Substitution Principle
        checks.extend(await self._check_liskov_substitution())
        
        # Interface Segregation Principle
        checks.extend(await self._check_interface_segregation())
        
        # Dependency Inversion Principle
        checks.extend(await self._check_dependency_inversion())
        
        self.results['solid_principles'] = checks
    
    async def _validate_design_patterns(self):
        """Validate design pattern implementations."""
        logger.info("Validating design patterns...")
        
        checks = []
        
        # Template Method Pattern
        checks.extend(await self._check_template_method_pattern())
        
        # Repository Pattern
        checks.extend(await self._check_repository_pattern())
        
        # CQRS Pattern
        checks.extend(await self._check_cqrs_pattern())
        
        # Event-Driven Architecture
        checks.extend(await self._check_event_driven_architecture())
        
        # Factory Pattern
        checks.extend(await self._check_factory_pattern())
        
        self.results['design_patterns'] = checks
    
    async def _validate_error_handling(self):
        """Validate error handling implementation."""
        logger.info("Validating error handling...")
        
        checks = []
        
        # Check exception handling in services
        try:
            from app.domains.announcements.service import AnnouncementService
            
            # Check if services have proper try-catch blocks
            source = inspect.getsource(AnnouncementService)
            
            if 'try:' in source and 'except' in source:
                checks.append({
                    'check': 'Services implement exception handling',
                    'status': 'PASS',
                    'details': 'Try-catch blocks found in service code'
                })
            else:
                checks.append({
                    'check': 'Services implement exception handling',
                    'status': 'FAIL',
                    'details': 'No exception handling found in service code'
                })
            
            # Check logging usage
            if 'logger' in source and 'logging' in source:
                checks.append({
                    'check': 'Services implement logging',
                    'status': 'PASS',
                    'details': 'Logging implementation found'
                })
            else:
                checks.append({
                    'check': 'Services implement logging',
                    'status': 'FAIL',
                    'details': 'No logging implementation found'
                })
        
        except Exception as e:
            checks.append({
                'check': 'Error handling validation',
                'status': 'FAIL',
                'details': f'Validation error: {e}'
            })
        
        self.results['error_handling'] = checks
    
    async def _validate_performance(self):
        """Validate performance characteristics."""
        logger.info("Validating performance characteristics...")
        
        checks = []
        
        # Check async/await usage
        try:
            from app.shared.interfaces.base_service import BaseService
            
            methods = inspect.getmembers(BaseService, predicate=inspect.isfunction)
            async_methods = [name for name, method in methods 
                           if inspect.iscoroutinefunction(method)]
            
            if async_methods:
                checks.append({
                    'check': 'Services use async/await pattern',
                    'status': 'PASS',
                    'details': f'Found {len(async_methods)} async methods'
                })
            else:
                checks.append({
                    'check': 'Services use async/await pattern',
                    'status': 'FAIL',
                    'details': 'No async methods found'
                })
        
        except Exception as e:
            checks.append({
                'check': 'Performance validation',
                'status': 'FAIL',
                'details': f'Validation error: {e}'
            })
        
        self.results['performance'] = checks
    
    async def _check_single_responsibility(self) -> List[Dict[str, Any]]:
        """Check Single Responsibility Principle."""
        checks = []
        
        try:
            from app.domains.announcements.service import AnnouncementService
            
            # Check method count (shouldn't be too many responsibilities)
            methods = [method for method in dir(AnnouncementService) 
                      if not method.startswith('_') and callable(getattr(AnnouncementService, method))]
            
            if len(methods) < 20:  # Reasonable number of public methods
                checks.append({
                    'check': 'Service has focused responsibility',
                    'status': 'PASS',
                    'details': f'Service has {len(methods)} public methods'
                })
            else:
                checks.append({
                    'check': 'Service has focused responsibility',
                    'status': 'WARNING',
                    'details': f'Service has {len(methods)} public methods (may be doing too much)'
                })
        
        except Exception as e:
            checks.append({
                'check': 'Single Responsibility Principle',
                'status': 'FAIL',
                'details': f'Check failed: {e}'
            })
        
        return checks
    
    async def _check_open_closed(self) -> List[Dict[str, Any]]:
        """Check Open/Closed Principle."""
        checks = []
        
        try:
            from app.shared.interfaces.base_service import BaseService
            
            # Check if BaseService is designed for extension
            source = inspect.getsource(BaseService)
            
            if 'ABC' in source and '@abstractmethod' in source:
                checks.append({
                    'check': 'BaseService is open for extension',
                    'status': 'PASS',
                    'details': 'Abstract base class with abstract methods'
                })
            else:
                checks.append({
                    'check': 'BaseService is open for extension',
                    'status': 'FAIL',
                    'details': 'BaseService is not properly abstract'
                })
        
        except Exception as e:
            checks.append({
                'check': 'Open/Closed Principle',
                'status': 'FAIL',
                'details': f'Check failed: {e}'
            })
        
        return checks
    
    async def _check_liskov_substitution(self) -> List[Dict[str, Any]]:
        """Check Liskov Substitution Principle."""
        checks = []
        
        try:
            from app.domains.announcements.service import AnnouncementService
            from app.shared.interfaces.base_service import BaseService
            
            # Check if service can be used as BaseService
            if issubclass(AnnouncementService, BaseService):
                checks.append({
                    'check': 'Services are substitutable for BaseService',
                    'status': 'PASS',
                    'details': 'Service properly inherits from BaseService'
                })
            else:
                checks.append({
                    'check': 'Services are substitutable for BaseService',
                    'status': 'FAIL',
                    'details': 'Service cannot be substituted for BaseService'
                })
        
        except Exception as e:
            checks.append({
                'check': 'Liskov Substitution Principle',
                'status': 'FAIL',
                'details': f'Check failed: {e}'
            })
        
        return checks
    
    async def _check_interface_segregation(self) -> List[Dict[str, Any]]:
        """Check Interface Segregation Principle."""
        checks = []
        
        try:
            # Check if interfaces are focused
            from app.shared.interfaces.domain_services import IAnnouncementService
            
            methods = [method for method in dir(IAnnouncementService) 
                      if not method.startswith('_')]
            
            if len(methods) < 15:  # Reasonable interface size
                checks.append({
                    'check': 'Interfaces are focused and segregated',
                    'status': 'PASS',
                    'details': f'Domain interface has {len(methods)} methods'
                })
            else:
                checks.append({
                    'check': 'Interfaces are focused and segregated',
                    'status': 'WARNING',
                    'details': f'Domain interface has {len(methods)} methods (may be too large)'
                })
        
        except Exception as e:
            checks.append({
                'check': 'Interface Segregation Principle',
                'status': 'FAIL',
                'details': f'Check failed: {e}'
            })
        
        return checks
    
    async def _check_dependency_inversion(self) -> List[Dict[str, Any]]:
        """Check Dependency Inversion Principle."""
        checks = []
        
        try:
            from app.domains.announcements.service import AnnouncementService
            
            # Check constructor for dependency injection
            init_signature = inspect.signature(AnnouncementService.__init__)
            params = list(init_signature.parameters.keys())
            
            if 'repository' in params:
                checks.append({
                    'check': 'Services depend on abstractions',
                    'status': 'PASS',
                    'details': 'Repository dependency injection found'
                })
            else:
                checks.append({
                    'check': 'Services depend on abstractions',
                    'status': 'FAIL',
                    'details': 'No dependency injection found'
                })
        
        except Exception as e:
            checks.append({
                'check': 'Dependency Inversion Principle',
                'status': 'FAIL',
                'details': f'Check failed: {e}'
            })
        
        return checks
    
    async def _check_template_method_pattern(self) -> List[Dict[str, Any]]:
        """Check Template Method Pattern implementation."""
        checks = []
        
        try:
            from app.shared.interfaces.base_service import BaseService
            
            # Check for template methods
            source = inspect.getsource(BaseService)
            
            if 'async def create(' in source and 'await self._' in source:
                checks.append({
                    'check': 'Template Method Pattern implemented',
                    'status': 'PASS',
                    'details': 'BaseService uses template method pattern'
                })
            else:
                checks.append({
                    'check': 'Template Method Pattern implemented',
                    'status': 'FAIL',
                    'details': 'Template method pattern not found'
                })
        
        except Exception as e:
            checks.append({
                'check': 'Template Method Pattern',
                'status': 'FAIL',
                'details': f'Check failed: {e}'
            })
        
        return checks
    
    async def _check_repository_pattern(self) -> List[Dict[str, Any]]:
        """Check Repository Pattern implementation."""
        checks = []
        
        try:
            # Check if repository interfaces exist
            from app.core.interfaces.base_repository import IRepository
            
            checks.append({
                'check': 'Repository Pattern interfaces exist',
                'status': 'PASS',
                'details': 'Repository interfaces found'
            })
        
        except ImportError:
            checks.append({
                'check': 'Repository Pattern interfaces exist',
                'status': 'FAIL',
                'details': 'Repository interfaces not found'
            })
        except Exception as e:
            checks.append({
                'check': 'Repository Pattern',
                'status': 'FAIL',
                'details': f'Check failed: {e}'
            })
        
        return checks
    
    async def _check_cqrs_pattern(self) -> List[Dict[str, Any]]:
        """Check CQRS Pattern implementation."""
        checks = []
        
        try:
            from app.shared.cqrs.commands import Command
            from app.shared.cqrs.queries import Query
            from app.shared.cqrs.bus import CommandBus, QueryBus
            
            checks.append({
                'check': 'CQRS Pattern implemented',
                'status': 'PASS',
                'details': 'Command and Query buses exist'
            })
        
        except ImportError:
            checks.append({
                'check': 'CQRS Pattern implemented',
                'status': 'FAIL',
                'details': 'CQRS components not found'
            })
        except Exception as e:
            checks.append({
                'check': 'CQRS Pattern',
                'status': 'FAIL',
                'details': f'Check failed: {e}'
            })
        
        return checks
    
    async def _check_event_driven_architecture(self) -> List[Dict[str, Any]]:
        """Check Event-Driven Architecture implementation."""
        checks = []
        
        try:
            from app.shared.events.domain_events import DomainEvent, EventBus
            from app.shared.events.event_store import EventStore
            
            checks.append({
                'check': 'Event-Driven Architecture implemented',
                'status': 'PASS',
                'details': 'Domain events and event bus exist'
            })
        
        except ImportError:
            checks.append({
                'check': 'Event-Driven Architecture implemented',
                'status': 'FAIL',
                'details': 'Event system components not found'
            })
        except Exception as e:
            checks.append({
                'check': 'Event-Driven Architecture',
                'status': 'FAIL',
                'details': f'Check failed: {e}'
            })
        
        return checks
    
    async def _check_factory_pattern(self) -> List[Dict[str, Any]]:
        """Check Factory Pattern implementation."""
        checks = []
        
        try:
            from app.shared.events.cross_domain_services import create_cross_domain_services
            
            checks.append({
                'check': 'Factory Pattern implemented',
                'status': 'PASS',
                'details': 'Factory functions for service creation exist'
            })
        
        except ImportError:
            checks.append({
                'check': 'Factory Pattern implemented',
                'status': 'FAIL',
                'details': 'Factory functions not found'
            })
        except Exception as e:
            checks.append({
                'check': 'Factory Pattern',
                'status': 'FAIL',
                'details': f'Check failed: {e}'
            })
        
        return checks
    
    def _calculate_overall_score(self):
        """Calculate overall validation score."""
        total_checks = 0
        passed_checks = 0
        
        for category, checks in self.results.items():
            if category == 'overall_score':
                continue
            
            for check in checks:
                total_checks += 1
                if check['status'] == 'PASS':
                    passed_checks += 1
        
        if total_checks > 0:
            self.results['overall_score'] = round((passed_checks / total_checks) * 100, 2)
        else:
            self.results['overall_score'] = 0
    
    def _get_abstract_methods(self, cls) -> List[str]:
        """Get list of abstract methods from a class."""
        abstract_methods = []
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if hasattr(method, '__isabstractmethod__') and method.__isabstractmethod__:
                abstract_methods.append(name)
        return abstract_methods
    
    def _implements_interface(self, cls, interface) -> bool:
        """Check if a class implements an interface."""
        try:
            # Check if all interface methods are implemented
            interface_methods = [method for method in dir(interface) 
                               if not method.startswith('_') and callable(getattr(interface, method))]
            
            cls_methods = [method for method in dir(cls) 
                          if not method.startswith('_') and callable(getattr(cls, method))]
            
            return all(method in cls_methods for method in interface_methods)
        except:
            return False
    
    def print_results(self):
        """Print validation results in a readable format."""
        print("\n" + "="*80)
        print("SERVICE LAYER VALIDATION RESULTS")
        print("="*80)
        
        for category, checks in self.results.items():
            if category == 'overall_score':
                continue
            
            print(f"\n{category.upper().replace('_', ' ')}")
            print("-" * 40)
            
            for check in checks:
                status_color = {
                    'PASS': '\033[92m',  # Green
                    'FAIL': '\033[91m',  # Red
                    'WARNING': '\033[93m'  # Yellow
                }
                reset_color = '\033[0m'
                
                color = status_color.get(check['status'], '')
                print(f"{color}[{check['status']}]{reset_color} {check['check']}")
                if check['details']:
                    print(f"    {check['details']}")
        
        print(f"\n{'='*80}")
        score = self.results['overall_score']
        if score >= 90:
            score_color = '\033[92m'  # Green
        elif score >= 70:
            score_color = '\033[93m'  # Yellow
        else:
            score_color = '\033[91m'  # Red
        
        print(f"OVERALL SCORE: {score_color}{score}%{reset_color}")
        print("="*80)


async def main():
    """Main validation function."""
    validator = ServiceLayerValidator()
    
    try:
        results = await validator.run_validation()
        validator.print_results()
        
        # Save results to file
        import json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"service_layer_validation_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\nResults saved to: {filename}")
        
        # Exit with appropriate code
        score = results['overall_score']
        if score >= 80:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure
    
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())