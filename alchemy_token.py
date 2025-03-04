import os
import requests
import logging
import threading
import datetime
from typing import Dict, Any, Optional

class AlchemyTokenManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(AlchemyTokenManager, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize token management with configuration from environment variables"""
        # Token storage
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        
        # Logging setup
        logging.basicConfig(level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s')
        
        # Tenant configurations
        self.tenants = {
            'default': {
                'base_url': os.getenv('ALCHEMY_BASE_URL', 'https://core-production.alchemy.cloud/core/api/v2/'),
                'record_url': os.getenv('ALCHEMY_RECORD_URL', 'https://app.alchemy.cloud/productcaseelnlims4uat/record/'),
                'access_token': os.getenv('ALCHEMY_ACCESS_TOKEN'),
                'refresh_token': os.getenv('ALCHEMY_REFRESH_TOKEN')
            }
        }

    def get_token_for_tenant(self, tenant_key: str = 'default') -> Optional[str]:
        """
        Get a valid access token for a specific tenant.
        Refreshes the token if it's expired or not set.
        
        :param tenant_key: Key for the tenant configuration
        :return: Access token or None if retrieval fails
        """
        if tenant_key not in self.tenants:
            logging.error(f"Unknown tenant: {tenant_key}")
            return None

        tenant_config = self.tenants[tenant_key]

        # Check if current token is valid
        if (self.access_token and self.token_expiry and 
            datetime.datetime.now() < self.token_expiry):
            return self.access_token

        # Attempt to refresh token
        try:
            refresh_url = f"{tenant_config['base_url'].rstrip('/')}/refresh-token"
            headers = {"Content-Type": "application/json"}
            payload = {"refreshToken": tenant_config['refresh_token']}

            logging.info(f"Attempting to refresh token for tenant {tenant_key}")
            response = requests.put(refresh_url, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()

            # Update tokens
            self.access_token = data.get('accessToken')
            self.refresh_token = data.get('refreshToken', tenant_config['refresh_token'])
            
            # Set token expiry (default to 1 hour minus 5 min buffer)
            expiry_seconds = int(data.get('expiresIn', 3600)) - 300
            self.token_expiry = datetime.datetime.now() + datetime.timedelta(seconds=expiry_seconds)

            logging.info(f"Token refreshed for tenant {tenant_key}, valid until {self.token_expiry}")
            return self.access_token

        except Exception as e:
            logging.error(f"Error refreshing token for tenant {tenant_key}: {e}")
            return None

    def send_to_alchemy(self, payload: Dict[str, Any], tenant_key: str = 'default') -> Dict[str, Any]:
        """
        Send data to Alchemy using tenant-specific configuration
        
        :param payload: Data payload to send
        :param tenant_key: Key for the tenant configuration
        :return: Response dictionary with status and details
        """
        tenant_config = self.tenants[tenant_key]
        
        # Get valid token
        token = self.get_token_for_tenant(tenant_key)
        if not token:
            error_msg = "Failed to obtain access token"
            logging.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

        # Construct API URL
        create_record_url = f"{tenant_config['base_url'].rstrip('/')}/create-record"

        # Prepare headers
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            # Send request
            logging.info(f"Sending payload to Alchemy: {payload}")
            response = requests.post(create_record_url, headers=headers, json=payload)
            response.raise_for_status()

            # Try to extract record ID
            record_id = None
            record_url = None
            try:
                response_data = response.json()
                # Various ways to extract record ID based on response structure
                if isinstance(response_data, list) and response_data:
                    record_id = response_data[0].get('id') or response_data[0].get('recordId')
                elif isinstance(response_data, dict):
                    record_id = response_data.get('id') or response_data.get('recordId')
                    if not record_id and 'data' in response_data:
                        data = response_data['data']
                        if isinstance(data, list) and data:
                            record_id = data[0].get('id') or data[0].get('recordId')

                # Construct record URL if ID found
                if record_id:
                    record_url = f"{tenant_config['record_url'].rstrip('/')}/{record_id}"

            except Exception as e:
                logging.warning(f"Could not extract record ID: {e}")

            return {
                "status": "success",
                "message": "Data successfully sent to Alchemy",
                "response": response.json(),
                "record_id": record_id,
                "record_url": record_url
            }

        except requests.exceptions.RequestException as e:
            logging.error(f"Request error sending to Alchemy: {e}")
            error_response = None
            if hasattr(e, 'response') and e.response:
                try:
                    error_response = e.response.json()
                except:
                    error_response = {"text": e.response.text}

            return {
                "status": "error",
                "message": str(e),
                "details": error_response
            }

def send_to_alchemy_with_token_management(payload: Dict[str, Any], tenant_key: str = 'default') -> Dict[str, Any]:
    """
    Wrapper function to send payload to Alchemy with token management
    
    :param payload: Data payload to send
    :param tenant_key: Key for the tenant configuration
    :return: Response dictionary with status and details
    """
    token_manager = AlchemyTokenManager()
    return token_manager.send_to_alchemy(payload, tenant_key)
