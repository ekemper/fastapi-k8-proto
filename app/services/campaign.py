from typing import Dict, Any, Optional, List
import re
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.job import Job, JobStatus
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignStart
try:
    from app.background_services.apollo_service import ApolloService
except ImportError:
    ApolloService = None
    
try:
    from app.background_services.instantly_service import InstantlyService
except ImportError:
    InstantlyService = None
from app.workers.tasks import celery_app

logger = logging.getLogger(__name__)


class CampaignService:
    """Service for managing campaign business logic."""
    
    def __init__(self):
        self.apollo_service = ApolloService() if ApolloService else None
        self.instantly_service = InstantlyService() if InstantlyService else None

    async def get_campaigns(self, db: Session) -> List[Dict[str, Any]]:
        """Get all campaigns with latest job information."""
        try:
            logger.info('Fetching all campaigns')
            
            campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
            logger.info(f'Found {len(campaigns)} campaigns')
            
            campaign_list = []
            for campaign in campaigns:
                try:
                    campaign_dict = campaign.to_dict()
                    
                    # Get latest job status for each campaign
                    latest_job = (
                        db.query(Job)
                        .filter_by(campaign_id=campaign.id)
                        .order_by(Job.created_at.desc())
                        .first()
                    )
                    if latest_job:
                        campaign_dict['latest_job'] = {
                            'id': latest_job.id,
                            'status': latest_job.status.value,
                            'created_at': latest_job.created_at.isoformat() if latest_job.created_at else None,
                            'completed_at': latest_job.completed_at.isoformat() if latest_job.completed_at else None,
                            'error': latest_job.error
                        }
                    else:
                        campaign_dict['latest_job'] = None
                        
                    campaign_list.append(campaign_dict)
                except Exception as e:
                    logger.error(f'Error converting campaign {campaign.id} to dict: {str(e)}', exc_info=True)
                    continue
            
            logger.info(f'Successfully converted {len(campaign_list)} campaigns to dict')
            return campaign_list
            
        except Exception as e:
            logger.error(f'Error getting campaigns: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching campaigns: {str(e)}"
            )

    async def get_campaign(self, campaign_id: str, db: Session) -> Dict[str, Any]:
        """Get a single campaign by ID."""
        try:
            logger.info(f'Fetching campaign {campaign_id}')
            
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                logger.warning(f'Campaign {campaign_id} not found')
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )
            
            campaign_dict = campaign.to_dict()
            
            # Get all jobs for this campaign (empty for now as per original logic)
            campaign_dict['jobs'] = []
            
            logger.info(f'Successfully fetched campaign {campaign_id}')
            return campaign_dict
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error getting campaign: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching campaign: {str(e)}"
            )

    async def create_campaign(self, campaign_data: CampaignCreate, db: Session) -> Dict[str, Any]:
        """Create a new campaign."""
        try:
            logger.info(f'Creating campaign: {campaign_data.name}')
            
            campaign = Campaign(
                name=campaign_data.name,
                description=campaign_data.description or '',
                organization_id=campaign_data.organization_id,
                status=CampaignStatus.CREATED,
                fileName=campaign_data.fileName,
                totalRecords=campaign_data.totalRecords,
                url=campaign_data.url
            )
            
            db.add(campaign)
            db.commit()
            db.refresh(campaign)

            # Create Instantly campaign
            if self.instantly_service:
                try:
                    instantly_response = self.instantly_service.create_campaign(name=campaign.name)
                    instantly_campaign_id = instantly_response.get('id')
                    if instantly_campaign_id:
                        campaign.instantly_campaign_id = instantly_campaign_id
                        db.commit()
                        logger.info(f"Created Instantly campaign with ID: {instantly_campaign_id}")
                    else:
                        logger.error(f"Instantly campaign creation failed: {instantly_response}")
                except Exception as e:
                    logger.error(f"Error calling InstantlyService.create_campaign: {str(e)}")
            else:
                logger.warning("InstantlyService not available, skipping campaign creation")

            logger.info(f'Successfully created campaign {campaign.id}')
            return campaign.to_dict()
            
        except Exception as e:
            db.rollback()
            logger.error(f'Error creating campaign: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating campaign: {str(e)}"
            )

    async def update_campaign(self, campaign_id: str, update_data: CampaignUpdate, db: Session) -> Dict[str, Any]:
        """Update campaign properties and return updated campaign."""
        try:
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )
            
            # Update only provided fields
            update_dict = update_data.dict(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(campaign, field, value)
            
            db.commit()
            db.refresh(campaign)
            
            logger.info(f'Successfully updated campaign {campaign_id}')
            return campaign.to_dict()
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f'Error updating campaign: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating campaign: {str(e)}"
            )

    async def start_campaign(self, campaign_id: str, start_data: CampaignStart, db: Session) -> Dict[str, Any]:
        """Start a campaign process."""
        try:
            logger.info(f"Starting campaign process for campaign_id={campaign_id}")

            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found during start.")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )

            if campaign.status != CampaignStatus.CREATED:
                logger.error(f"Cannot start campaign {campaign_id} in status {campaign.status}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot start campaign in {campaign.status.value} status"
                )

            # Validate URL and count
            self.validate_search_url(campaign.url)
            self.validate_count(campaign.totalRecords)

            # Update campaign status to RUNNING
            campaign.update_status(CampaignStatus.RUNNING, "Starting campaign process")
            db.commit()
            logger.info(f"Campaign {campaign_id} status updated to RUNNING")

            job_params = {
                'fileName': campaign.fileName,
                'totalRecords': campaign.totalRecords,
                'url': campaign.url
            }
            logger.info(f"Creating fetch_leads job for campaign {campaign_id} with params: {job_params}")

            # Create fetch leads job
            fetch_leads_job = Job(
                campaign_id=campaign_id,
                name='FETCH_LEADS',
                description=f'Fetch leads for campaign {campaign.name}',
                status=JobStatus.PENDING
            )
            db.add(fetch_leads_job)
            db.commit()
            db.refresh(fetch_leads_job)
            
            logger.info(f"Created fetch_leads job with id={fetch_leads_job.id} for campaign {campaign_id}")

            # Enqueue Apollo scraping and lead saving as a background job
            logger.info(f"Enqueuing fetch_and_save_leads_task for campaign {campaign_id}")
            task = fetch_and_save_leads.delay(job_params, campaign_id, fetch_leads_job.id)
            
            # Update job with task ID
            fetch_leads_job.task_id = task.id
            db.commit()

            logger.info(f'Successfully started campaign {campaign_id}')
            return campaign.to_dict()

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error starting campaign {campaign_id}: {str(e)}", exc_info=True)
            
            # Update campaign status to failed
            try:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if campaign:
                    campaign.update_status(CampaignStatus.FAILED, error_message=str(e))
                    db.commit()
            except Exception as inner_e:
                logger.error(f"Error updating campaign status to failed: {str(inner_e)}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error starting campaign: {str(e)}"
            )

    def validate_search_url(self, url: str) -> bool:
        """Validate Apollo search URL."""
        logger.info(f"Validating search URL: {url}")
        
        if not url:
            error_msg = "Search URL is required"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        if not isinstance(url, str):
            error_msg = "Search URL must be a string"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Basic URL validation
        if not url.startswith('https://app.apollo.io/'):
            error_msg = "Invalid Apollo search URL format"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Check for malicious URLs
        if re.search(r'[<>{}|\^~\[\]`]', url):
            error_msg = "URL contains invalid characters"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return True

    def validate_count(self, count: int) -> bool:
        """Validate the count parameter."""
        logger.info(f"Validating count parameter: {count}")
        
        if not isinstance(count, int):
            error_msg = "Count must be an integer"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        if count <= 0:
            error_msg = "Count must be greater than 0"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        if count > 1000:
            error_msg = "Count cannot exceed 1000"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return True

    async def cleanup_campaign_jobs(self, campaign_id: str, days: int, db: Session) -> Dict[str, Any]:
        """Clean up old jobs for a campaign."""
        try:
            logger.info(f"Cleaning up jobs for campaign {campaign_id} older than {days} days")

            # Get campaign
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )

            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Get jobs to delete
            jobs = (
                db.query(Job)
                .filter(
                    Job.campaign_id == campaign_id,
                    Job.created_at < cutoff_date,
                    Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED])
                )
                .all()
            )

            # Delete jobs
            for job in jobs:
                db.delete(job)

            db.commit()

            logger.info(f"Successfully cleaned up {len(jobs)} jobs for campaign {campaign_id}")
            return {
                'message': f'Successfully cleaned up {len(jobs)} jobs',
                'jobs_deleted': len(jobs)
            }

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error cleaning up campaign jobs: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error cleaning up campaign jobs: {str(e)}"
            )

    async def get_campaign_lead_stats(self, campaign_id: str, db: Session) -> Dict[str, Any]:
        """Return stats for a campaign's leads."""
        try:
            # Check if campaign exists
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )

            # Note: Lead model is not yet implemented in this FastAPI app
            # This is a placeholder that returns zero stats
            # TODO: Implement Lead model and actual lead statistics
            
            return {
                'total_leads_fetched': 0,
                'leads_with_email': 0,
                'leads_with_verified_email': 0,
                'leads_with_enrichment': 0,
                'leads_with_email_copy': 0,
                'leads_with_instantly_record': 0,
                'error_message': None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            error_str = f"Error in get_campaign_lead_stats for campaign {campaign_id}: {str(e)}"
            logger.error(error_str, exc_info=True)
            return {
                'total_leads_fetched': 0,
                'leads_with_email': 0,
                'leads_with_verified_email': 0,
                'leads_with_enrichment': 0,
                'leads_with_email_copy': 0,
                'leads_with_instantly_record': 0,
                'error_message': error_str
            }

    async def get_campaign_instantly_analytics(self, campaign_id: str, db: Session) -> Dict[str, Any]:
        """Fetch and map Instantly analytics overview for a campaign."""
        try:
            # Get campaign
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )
            
            campaign_dict = campaign.to_dict()
            instantly_campaign_id = campaign_dict.get('instantly_campaign_id')
            
            if not instantly_campaign_id:
                return {"error": "No Instantly campaign ID associated with this campaign."}
            
            # Fetch analytics from Instantly
            if not self.instantly_service:
                return {"error": "InstantlyService not available"}
                
            analytics = self.instantly_service.get_campaign_analytics_overview(instantly_campaign_id)
            if 'error' in analytics:
                return {"error": analytics['error']}
            
            # Map Instantly analytics response to required fields
            mapped = {
                "leads_count": analytics.get("leads_count") or campaign_dict.get("totalRecords"),
                "contacted_count": analytics.get("contacted_count") or analytics.get("new_leads_contacted_count"),
                "emails_sent_count": analytics.get("emails_sent_count"),
                "open_count": analytics.get("open_count"),
                "link_click_count": analytics.get("link_click_count"),
                "reply_count": analytics.get("reply_count"),
                "bounced_count": analytics.get("bounced_count"),
                "unsubscribed_count": analytics.get("unsubscribed_count"),
                "completed_count": analytics.get("completed_count"),
                "new_leads_contacted_count": analytics.get("new_leads_contacted_count"),
                "total_opportunities": analytics.get("total_opportunities"),
                # Campaign status info
                "campaign_name": campaign_dict.get("name"),
                "campaign_id": campaign_dict.get("id"),
                "campaign_status": campaign_dict.get("status"),
                "campaign_is_evergreen": analytics.get("is_evergreen", False),
            }
            
            return mapped
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting campaign analytics: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching campaign analytics: {str(e)}"
            )


# Celery task for fetching and saving leads
@celery_app.task(bind=True, name="fetch_and_save_leads")
def fetch_and_save_leads(self, job_params: Dict[str, Any], campaign_id: str, job_id: int):
    """Background task to fetch and save leads from Apollo."""
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Update job status to processing
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = JobStatus.PROCESSING
        job.task_id = self.request.id
        db.commit()
        
        # Initialize Apollo service and fetch leads
        try:
            from app.background_services.apollo_service import ApolloService
            apollo_service = ApolloService()
            result = apollo_service.fetch_leads(job_params, campaign_id, db)
        except ImportError:
            logger.error("ApolloService not available")
            result = {'count': 0, 'errors': ['ApolloService not available']}
        
        # Update job status to completed
        job.status = JobStatus.COMPLETED
        job.result = f"Fetched {result.get('count', 0)} leads"
        job.completed_at = datetime.utcnow()
        
        # Update campaign status
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.update_status(
                CampaignStatus.COMPLETED,
                f"Successfully fetched {result.get('count', 0)} leads"
            )
        
        db.commit()
        
        return {
            "job_id": job_id,
            "campaign_id": campaign_id,
            "status": "completed",
            "result": result
        }
        
    except Exception as e:
        # Mark job as failed
        if 'job' in locals() and job:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            
        # Mark campaign as failed
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.update_status(CampaignStatus.FAILED, error_message=str(e))
            
        db.commit()
        raise
        
    finally:
        db.close() 