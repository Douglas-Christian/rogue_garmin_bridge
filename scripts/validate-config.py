#!/usr/bin/env python3
"""
Configuration validation script for Rogue Garmin Bridge.
Validates environment configuration before deployment.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any


class ConfigValidator:
    """Validates configuration for different environments."""
    
    def __init__(self, env_file: str, environment: str):
        self.env_file = env_file
        self.environment = environment
        self.config = {}
        self.errors = []
        self.warnings = []
        
    def load_config(self) -> bool:
        """Load configuration from environment file."""
        if not os.path.exists(self.env_file):
            self.errors.append(f"Environment file not found: {self.env_file}")
            return False
            
        try:
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.config[key.strip()] = value.strip()
            return True
        except Exception as e:
            self.errors.append(f"Failed to load config: {e}")
            return False
    
    def validate_required_vars(self) -> None:
        """Validate required environment variables."""
        required_vars = {
            'production': [
                'SECRET_KEY',
            ],
            'staging': [],
            'development': []
        }
        
        env_required = required_vars.get(self.environment, [])
        
        for var in env_required:
            if not self.config.get(var):
                self.errors.append(f"Required variable missing: {var}")
            elif var == 'SECRET_KEY' and self.config[var] in [
                'your-secret-key-here', 
                'dev-secret-key', 
                'staging-secret-key-change-me'
            ]:
                self.errors.append(f"SECRET_KEY must be changed from default value")
    
    def validate_ports(self) -> None:
        """Validate port configurations."""
        port_vars = ['APP_PORT', 'PROMETHEUS_PORT', 'GRAFANA_PORT', 'HTTP_PORT', 'HTTPS_PORT']
        
        for var in port_vars:
            if var in self.config:
                try:
                    port = int(self.config[var])
                    if port < 1 or port > 65535:
                        self.errors.append(f"Invalid port range for {var}: {port}")
                    elif port < 1024 and self.environment == 'production':
                        self.warnings.append(f"Port {port} for {var} requires root privileges")
                except ValueError:
                    self.errors.append(f"Invalid port value for {var}: {self.config[var]}")
    
    def validate_paths(self) -> None:
        """Validate file and directory paths."""
        path_vars = ['DATA_PATH', 'LOGS_PATH', 'FIT_FILES_PATH']
        
        for var in path_vars:
            if var in self.config:
                path = Path(self.config[var])
                
                # Check if path is absolute in production
                if self.environment == 'production' and not path.is_absolute():
                    if not str(path).startswith('./'):
                        self.warnings.append(f"Consider using absolute path for {var} in production")
                
                # Check if parent directory exists for relative paths
                if not path.is_absolute() and not path.parent.exists():
                    self.warnings.append(f"Parent directory does not exist for {var}: {path.parent}")
    
    def validate_database(self) -> None:
        """Validate database configuration."""
        db_url = self.config.get('DATABASE_URL', '')
        
        if not db_url:
            self.errors.append("DATABASE_URL is required")
            return
        
        if db_url.startswith('sqlite:///'):
            db_path = db_url.replace('sqlite:///', '')
            
            # Check if database directory exists
            db_dir = Path(db_path).parent
            if not db_dir.exists():
                self.warnings.append(f"Database directory does not exist: {db_dir}")
            
            # Check for development database in production
            if self.environment == 'production' and 'dev' in db_path.lower():
                self.warnings.append("Using development database name in production")
        
        elif not db_url.startswith(('postgresql://', 'mysql://', 'sqlite://')):
            self.errors.append(f"Unsupported database URL format: {db_url}")
    
    def validate_logging(self) -> None:
        """Validate logging configuration."""
        log_level = self.config.get('LOG_LEVEL', 'INFO')
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        
        if log_level.upper() not in valid_levels:
            self.errors.append(f"Invalid LOG_LEVEL: {log_level}. Must be one of {valid_levels}")
        
        # Warn about debug logging in production
        if self.environment == 'production' and log_level.upper() == 'DEBUG':
            self.warnings.append("DEBUG logging enabled in production - may impact performance")
    
    def validate_security(self) -> None:
        """Validate security-related configuration."""
        # Check simulator usage in production
        if self.environment == 'production':
            use_simulator = self.config.get('USE_SIMULATOR', 'false').lower()
            if use_simulator == 'true':
                self.warnings.append("Simulator is enabled in production environment")
        
        # Check rate limiting
        rate_limit = self.config.get('API_RATE_LIMIT', '')
        if rate_limit and 'per minute' not in rate_limit:
            self.warnings.append("API_RATE_LIMIT format may be incorrect")
    
    def validate_numeric_values(self) -> None:
        """Validate numeric configuration values."""
        numeric_vars = {
            'CONNECTION_TIMEOUT': (1, 300),
            'RECONNECTION_ATTEMPTS': (1, 10),
            'RECONNECTION_DELAY': (1, 60),
            'DATA_RETENTION_DAYS': (1, 3650),
            'MAX_FIT_FILE_AGE_DAYS': (1, 365),
            'CACHE_TIMEOUT': (1, 3600)
        }
        
        for var, (min_val, max_val) in numeric_vars.items():
            if var in self.config:
                try:
                    value = int(self.config[var])
                    if value < min_val or value > max_val:
                        self.errors.append(f"{var} value {value} outside valid range ({min_val}-{max_val})")
                except ValueError:
                    self.errors.append(f"Invalid numeric value for {var}: {self.config[var]}")
    
    def validate_boolean_values(self) -> None:
        """Validate boolean configuration values."""
        boolean_vars = [
            'USE_SIMULATOR', 'METRICS_ENABLED', 'HEALTH_CHECK_ENABLED',
            'HEALTH_CHECK_DATABASE', 'HEALTH_CHECK_BLUETOOTH',
            'HEALTH_CHECK_DISK_SPACE', 'HEALTH_CHECK_MEMORY'
        ]
        
        for var in boolean_vars:
            if var in self.config:
                value = self.config[var].lower()
                if value not in ['true', 'false', '1', '0', 'yes', 'no']:
                    self.errors.append(f"Invalid boolean value for {var}: {self.config[var]}")
    
    def validate_all(self) -> Tuple[List[str], List[str]]:
        """Run all validations and return errors and warnings."""
        if not self.load_config():
            return self.errors, self.warnings
        
        self.validate_required_vars()
        self.validate_ports()
        self.validate_paths()
        self.validate_database()
        self.validate_logging()
        self.validate_security()
        self.validate_numeric_values()
        self.validate_boolean_values()
        
        return self.errors, self.warnings
    
    def print_results(self) -> bool:
        """Print validation results and return success status."""
        print(f"Validating configuration for {self.environment} environment...")
        print(f"Environment file: {self.env_file}")
        print()
        
        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()
        
        if self.errors:
            print("❌ ERRORS:")
            for error in self.errors:
                print(f"  - {error}")
            print()
            print("❌ Configuration validation FAILED")
            return False
        else:
            print("✅ Configuration validation PASSED")
            if self.warnings:
                print(f"   ({len(self.warnings)} warnings)")
            return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Validate Rogue Garmin Bridge configuration')
    parser.add_argument('environment', choices=['development', 'staging', 'production', 'raspberry-pi', 'rpi'],
                       help='Environment to validate')
    parser.add_argument('--env-file', help='Environment file to validate')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Only show errors, suppress warnings')
    
    args = parser.parse_args()
    
    # Determine environment file
    if args.env_file:
        env_file = args.env_file
    elif args.environment in ('raspberry-pi', 'rpi'):
        env_file = '.env.rpi'
    elif args.environment == 'staging':
        env_file = '.env.staging'
    else:
        env_file = '.env'
    
    # Validate configuration
    validator = ConfigValidator(env_file, args.environment)
    errors, warnings = validator.validate_all()
    
    # Filter warnings if quiet mode
    if args.quiet:
        validator.warnings = []
    
    # Print results
    success = validator.print_results()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()