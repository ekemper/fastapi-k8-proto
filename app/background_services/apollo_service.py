import os
from apify_client import ApifyClient
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import random
import time
from datetime import datetime
import json
import traceback
import apify_client
from sqlalchemy.orm import Session
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.models.job import Job, JobStatus
from app.schemas.lead import LeadCreate
from app.core.database import get_db
from app.core.logger import get_logger
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter
from app.background_services.smoke_tests.mock_apify_client import MockApifyClient

logger = get_logger(__name__)

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
    """
    Service for interacting with the Apollo API via Apify.
    
    This service now supports rate limiting to prevent exceeding API limits
    and avoid IP blocking. Rate limiting is optional to maintain backward 
    compatibility with existing code.
    
    Note: Apollo service typically handles bulk operations, so rate limiting
    is applied per API call rather than per lead processed.
    """
    
    def __init__(self, rate_limiter: Optional[ApiIntegrationRateLimiter] = None):
        """
        Initialize the Apollo service.
        
        Args:
            rate_limiter: Optional rate limiter for Apollo/Apify API calls.
                         If not provided, no rate limiting will be applied.
        """
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
        self.rate_limiter = rate_limiter
        
        # Log rate limiting status for monitoring
        if self.rate_limiter:
            logger.info(
                f"ApolloService initialized with rate limiting: "
                f"{self.rate_limiter.max_requests} requests per {self.rate_limiter.period_seconds}s",
                extra={'component': 'apollo_service', 'rate_limiting': 'enabled'}
            )
        else:
            logger.info(
                "ApolloService initialized without rate limiting",
                extra={'component': 'apollo_service', 'rate_limiting': 'disabled'}
            )

    def _save_leads_to_db(self, leads_data: List[Dict[str, Any]], campaign_id: str, db) -> int:
        """
        Helper to save leads to the database session and commit.
        Returns the number of leads created.
        """
        if not db:
            logger.warning("No database session provided, skipping lead save")
            return 0
            
        created_count = 0
        for lead_data in leads_data:
            try:
                # Extract company name from organization or use organization_name field
                company = None
                if 'organization' in lead_data and lead_data['organization']:
                    company = lead_data['organization'].get('name')
                elif 'organization_name' in lead_data:
                    company = lead_data['organization_name']
                
                # Create Lead object
                lead = Lead(
                    campaign_id=campaign_id,
                    first_name=lead_data.get('first_name'),
                    last_name=lead_data.get('last_name'),
                    email=lead_data.get('email'),
                    phone=lead_data.get('phone'),
                    company=company,
                    title=lead_data.get('title'),
                    linkedin_url=lead_data.get('linkedin_url'),
                    raw_data=lead_data  # Store the full raw data
                )
                
                db.add(lead)
                created_count += 1
                logger.info(f"[LEAD] Created lead: {lead.email} for campaign {campaign_id}")
                
            except Exception as e:
                logger.error(f"[LEAD] Error creating lead from data {lead_data.get('email', 'unknown')}: {str(e)}")
                continue
        
        # Commit all leads at once
        try:
            db.commit()
            logger.info(f"[LEAD] Successfully saved {created_count} leads for campaign {campaign_id}")
        except Exception as e:
            logger.error(f"[LEAD] Error committing leads to database: {str(e)}")
            db.rollback()
            raise
            
        return created_count

    def fetch_leads(self, params: Dict[str, Any], campaign_id: str, db=None) -> Dict[str, Any]:
        """
        Fetch leads from Apollo via Apify and save them to the database.
        
        This method now includes rate limiting support to prevent exceeding
        API limits. If rate limiting is enabled and the limit is exceeded,
        the method will return an error response.
        
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
        
        # Check rate limiting if enabled
        if self.rate_limiter:
            try:
                if not self.rate_limiter.acquire():
                    remaining = self.rate_limiter.get_remaining()
                    error_msg = (
                        f"Rate limit exceeded for Apollo/Apify API. "
                        f"Remaining requests: {remaining}. "
                        f"Try again in {self.rate_limiter.period_seconds} seconds."
                    )
                    logger.warning(
                        f"Rate limit exceeded for Apollo leads fetch: campaign {campaign_id}",
                        extra={
                            'component': 'apollo_service',
                            'rate_limit_exceeded': True,
                            'remaining_requests': remaining,
                            'campaign_id': campaign_id
                        }
                    )
                    return {
                        'count': 0,
                        'errors': [error_msg],
                        'rate_limited': True,
                        'remaining_requests': remaining,
                        'retry_after_seconds': self.rate_limiter.period_seconds
                    }
            except Exception as rate_limit_error:
                # If rate limiter fails (e.g., Redis unavailable), log and continue
                logger.warning(
                    f"Rate limiter error, proceeding without rate limiting: {rate_limit_error}",
                    extra={'component': 'apollo_service', 'rate_limiter_error': str(rate_limit_error)}
                )
        
        try:
            logger.info(f"[START fetch_leads] campaign_id={campaign_id}")

            # --- Apify actor run block ---
            logger.info(f"[BEFORE ApifyClient actor call] actor_id={self.actor_id} with params: {params}")
            
            # Log rate limiting status for monitoring
            if self.rate_limiter:
                remaining_before = self.rate_limiter.get_remaining()
                logger.info(
                    f"Making Apollo API call with rate limiter remaining: {remaining_before}",
                    extra={
                        'component': 'apollo_service',
                        'rate_limiter_remaining_before': remaining_before,
                        'campaign_id': campaign_id
                    }
                )
            
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
            
            # Log rate limiting status after successful call
            if self.rate_limiter:
                remaining_after = self.rate_limiter.get_remaining()
                logger.info(
                    f"Apollo API call successful. Rate limiter remaining: {remaining_after}",
                    extra={
                        'component': 'apollo_service',
                        'rate_limiter_remaining_after': remaining_after,
                        'campaign_id': campaign_id,
                        'leads_fetched': created_count
                    }
                )
            else:
                logger.info(
                    f"Apollo API call successful",
                    extra={
                        'component': 'apollo_service',
                        'campaign_id': campaign_id,
                        'leads_fetched': created_count
                    }
                )
            
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