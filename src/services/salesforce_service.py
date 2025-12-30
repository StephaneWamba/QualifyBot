"""Salesforce service for CRM operations."""

from simple_salesforce import Salesforce

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class SalesforceService:
    """Service for Salesforce operations."""

    def __init__(self):
        """Initialize Salesforce client."""
        self.client = None
        self._initialized = False

    async def _ensure_connected(self):
        """Ensure Salesforce connection is established."""
        if not self._initialized:
            try:
                domain = "test" if settings.SALESFORCE_DOMAIN == "test" else "login"
                self.client = Salesforce(
                    username=settings.SALESFORCE_USERNAME,
                    password=settings.SALESFORCE_PASSWORD,
                    security_token=settings.SALESFORCE_SECURITY_TOKEN,
                    domain=domain,
                )
                self._initialized = True
                logger.info("Salesforce connection established")
            except Exception as e:
                logger.error("Failed to connect to Salesforce", error=str(e))
                raise

    async def create_lead(self, lead_data: dict) -> str:
        """
        Create a lead in Salesforce.

        Args:
            lead_data: Lead data dictionary

        Returns:
            Lead ID
        """
        await self._ensure_connected()
        
        try:
            # Remove None values
            clean_data = {k: v for k, v in lead_data.items() if v is not None}
            
            result = self.client.Lead.create(clean_data)
            lead_id = result["id"]
            
            logger.info("Lead created in Salesforce", lead_id=lead_id, data=clean_data)
            return lead_id
        except Exception as e:
            logger.error("Failed to create Salesforce lead", error=str(e), data=lead_data)
            raise


# Singleton instance
salesforce_service = SalesforceService()


