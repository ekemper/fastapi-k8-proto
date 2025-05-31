import os
import openai
from openai import OpenAI
from app.models.lead import Lead
from typing import Dict, Any, Optional
from app.core.logger import get_logger
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter

logger = get_logger(__name__)

class OpenAIService:
    """
    Service for generating email copy using OpenAI's API.
    
    This service now supports rate limiting to prevent exceeding API limits
    and avoid IP blocking. Rate limiting is optional to maintain backward 
    compatibility with existing code.
    """

    def __init__(self, rate_limiter: Optional[ApiIntegrationRateLimiter] = None):
        """
        Initialize the OpenAIService.
        
        Args:
            rate_limiter: Optional rate limiter for OpenAI API calls.
                         If not provided, no rate limiting will be applied.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = OpenAI(api_key=api_key)
        self.rate_limiter = rate_limiter
        
        # Log rate limiting status for monitoring
        if self.rate_limiter:
            logger.info(
                f"OpenAIService initialized with rate limiting: "
                f"{self.rate_limiter.max_requests} requests per {self.rate_limiter.period_seconds}s",
                extra={'component': 'openai_service', 'rate_limiting': 'enabled'}
            )
        else:
            logger.info(
                "OpenAIService initialized without rate limiting",
                extra={'component': 'openai_service', 'rate_limiting': 'disabled'}
            )

    def _check_rate_limit(self, operation: str) -> dict:
        """
        Check rate limiting if enabled.
        
        Args:
            operation: The operation being performed for logging
            
        Returns:
            dict: Error response if rate limited, None if allowed
        """
        if self.rate_limiter:
            try:
                if not self.rate_limiter.acquire():
                    remaining = self.rate_limiter.get_remaining()
                    error_msg = (
                        f"Rate limit exceeded for OpenAI API. "
                        f"Remaining requests: {remaining}. "
                        f"Try again in {self.rate_limiter.period_seconds} seconds."
                    )
                    logger.warning(
                        f"Rate limit exceeded for {operation}",
                        extra={
                            'component': 'openai_service',
                            'rate_limit_exceeded': True,
                            'remaining_requests': remaining,
                            'operation': operation
                        }
                    )
                    return {
                        'status': 'rate_limited',
                        'error': error_msg,
                        'remaining_requests': remaining,
                        'retry_after_seconds': self.rate_limiter.period_seconds
                    }
            except Exception as rate_limit_error:
                # If rate limiter fails (e.g., Redis unavailable), log and continue
                logger.warning(
                    f"Rate limiter error, proceeding without rate limiting: {rate_limit_error}",
                    extra={'component': 'openai_service', 'rate_limiter_error': str(rate_limit_error)}
                )
        return None

    def generate_email_copy(self, lead: Lead, enrichment_data: Dict[str, Any]) -> dict:
        """
        Generate personalized email copy for a lead.
        
        This method now includes rate limiting support to prevent exceeding
        API limits. If rate limiting is enabled and the limit is exceeded,
        the method will return an error response.
        
        Args:
            lead: The lead to generate email copy for
            enrichment_data: Additional data about the lead
        Returns:
            The full OpenAI API response (dict) or error response
        """
        # Check rate limiting if enabled
        rate_limit_error = self._check_rate_limit(f"generate_email_copy for lead {getattr(lead, 'id', None)}")
        if rate_limit_error:
            return rate_limit_error
        
        try:
            # Extract and log prompt variables
            first_name = getattr(lead, 'first_name', '')
            last_name = getattr(lead, 'last_name', '')
            company_name = getattr(lead, 'company_name', None) or getattr(lead, 'company', '')
            full_name = f"{first_name} {last_name}".strip()
            
            logger.info(
                f"Email copy prompt vars for lead {getattr(lead, 'id', None)}: first_name='{first_name}', last_name='{last_name}', company_name='{company_name}'", 
                extra={'component': 'openai_service', 'lead_id': getattr(lead, 'id', None)}
            )

            # Validate required fields
            missing = []
            if not first_name:
                missing.append('first_name')
            if not last_name:
                missing.append('last_name')
            if not company_name:
                missing.append('company_name')
            if missing:
                error_msg = f"Missing required prompt variables for email copy: {', '.join(missing)} for lead {getattr(lead, 'id', None)}"
                logger.error(
                    error_msg, 
                    extra={'component': 'openai_service', 'lead_id': getattr(lead, 'id', None), 'missing_fields': missing}
                )
                raise ValueError(error_msg)

            # Extract enrichment content
            enrichment_content = ""
            if enrichment_data and 'choices' in enrichment_data:
                enrichment_content = enrichment_data['choices'][0]['message']['content']

            prompt = f"""Write a personalized email to {full_name} at {company_name}.

Enrichment Information:
{enrichment_content}

Lead Information:
- Name: {full_name}
- Company: {company_name}
- Role: {getattr(lead, 'title', 'Unknown')}

Write a professional, personalized email that:
1. Shows understanding of their business
2. Offers specific value
3. Has a clear call to action
4. Is concise and engaging

Email:"""

            logger.info(
                f"Built email copy prompt for lead {getattr(lead, 'id', None)}", 
                extra={'component': 'openai_service', 'lead_id': getattr(lead, 'id', None)}
            )

            # Call OpenAI API (openai>=1.0.0 interface)
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional email copywriter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            result = response.model_dump()
            
            # Log rate limiting status for monitoring
            if self.rate_limiter:
                remaining = self.rate_limiter.get_remaining()
                logger.info(
                    f"Email copy generation successful for lead {getattr(lead, 'id', None)}. Rate limiter remaining: {remaining}",
                    extra={
                        'component': 'openai_service',
                        'lead_id': getattr(lead, 'id', None),
                        'rate_limiter_remaining': remaining
                    }
                )
            else:
                logger.info(
                    f"Email copy generation successful for lead {getattr(lead, 'id', None)}",
                    extra={'component': 'openai_service', 'lead_id': getattr(lead, 'id', None)}
                )
            
            return result
            
        except Exception as e:
            error_msg = f"Error generating email copy for lead {getattr(lead, 'id', None)}: {str(e)}"
            logger.error(
                error_msg, 
                extra={'component': 'openai_service', 'lead_id': getattr(lead, 'id', None), 'error': str(e)}
            )
            
            # Return error in same format as other services for consistency
            return {
                'status': 'error',
                'error': str(e)
            } 