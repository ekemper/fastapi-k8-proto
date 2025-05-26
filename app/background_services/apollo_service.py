import os
from apify_client import ApifyClient
from typing import Dict, Any, List
from dotenv import load_dotenv
import random
import time
from datetime import datetime
import json
import traceback
import apify_client
import logging
from app.background_services.mock_apify_client import MockApifyClient

logger = logging.getLogger(__name__)

"""
IMPORTANT: Apify Python client (v1.10.0 and some other versions) expects webhook payload keys in snake_case (e.g., 'event_types', 'request_url', 'payload_template', 'idempotency_key'),
even though the official Apify API docs use camelCase (e.g., 'eventTypes', 'requestUrl', 'payloadTemplate', 'idempotencyKey').

If you use camelCase keys, you will get KeyError exceptions from the client library (e.g., 'event_types', 'request_url').

References:
- https://docs.apify.com/platform/integrations/webhooks/events (API docs, camelCase)
- https://github.com/apify/apify-client-python/blob/master/src/apify_client/_utils.py (client expects snake_case)
- Error example: KeyError: 'event_types' or 'request_url' in encode_webhook_list_to_base64

This is an exception to the usual rule of following the API docs exactly. Always use snake_case keys in webhook payloads when using the Apify Python client.
"""

class ApolloService:
    """Service for interacting with the Apollo API."""
    
    def __init__(self):
        """Initialize the Apollo service."""
        load_dotenv()
        self.api_token = os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN environment variable is not set")
        # Use mock client if env var is set
        use_mock = os.getenv("USE_APIFY_CLIENT_MOCK", "false").lower() == "true"
        if use_mock:
            self.client = MockApifyClient(self.api_token)
        else:
            self.client = ApifyClient(self.api_token)
        self.actor_id = "code_crafter/apollo-io-scraper"
        # self.actor_id = "supreme_coder/apollo-scraper"

    def _save_leads_to_db(self, leads_data: List[Dict[str, Any]], campaign_id: str, db) -> int:
        """
        Helper to save leads to the database session and commit.
        Returns the number of leads created.
        Note: Lead model is not yet implemented in FastAPI app, so this is a placeholder.
        """
        created_count = len(leads_data)  # Simulate saving leads
        logger.info(f"[LEAD] Simulated saving {created_count} leads for campaign {campaign_id}")
        # TODO: Implement actual Lead model and database saving
        return created_count

    def fetch_leads(self, params: Dict[str, Any], campaign_id: str, db=None) -> Dict[str, Any]:
        """
        Fetch leads from Apollo and save them to the database.
        Args:
            params: Parameters for the Apollo API (must include fileName, totalRecords, url)
            campaign_id: ID of the campaign to associate leads with
            db: Database session (optional, for FastAPI integration)
        Returns:
            Dict containing the count of created leads and any errors
        """
        # Validate input shape
        required_keys = ['fileName', 'totalRecords', 'url']
        for key in required_keys:
            if key not in params:
                raise ValueError(f"Missing required parameter: {key} (expected keys: {required_keys})")
        logger.info(f"[APIFY] fetch_leads input params: {params}")
        try:
            logger.info(f"[START fetch_leads] campaign_id={campaign_id}")

            # --- Apify actor run block ---
            logger.info(f"[BEFORE ApifyClient actor call] actor_id={self.actor_id} with params: {params}")
            run = self.client.actor(self.actor_id).call(run_input=params)
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                raise Exception("No dataset ID returned from Apify actor run.")
            logger.info(f"[GOT dataset_id] {dataset_id}")
            results = list(self.client.dataset(dataset_id).iterate_items())
            logger.info(f"[AFTER dataset.iterate_items] got {len(results)} results")

            # Process and save leads using helper
            errors = []
            try:
                created_count = self._save_leads_to_db(results, campaign_id, db)
            except Exception as e:
                error_msg = f"Error saving leads: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                created_count = 0
            
            logger.info(f"[AFTER _save_leads_to_db] created_count={created_count}")
            logger.info(f"Leads fetch complete: {created_count} leads created, {len(errors)} errors")
            return {
                'count': created_count,
                'errors': errors
            }
            
        except Exception as e:
            error_msg = f"Error fetching leads: {str(e)}"
            logger.error(error_msg)
            raise 