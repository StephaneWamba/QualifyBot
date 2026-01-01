"""Database migration script for support_tickets table."""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


async def apply_ticket_migrations():
    """Apply database migrations to create support_tickets table."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        # Create support_tickets table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id SERIAL PRIMARY KEY,
                ticket_id VARCHAR(100) UNIQUE NOT NULL,
                call_sid VARCHAR(100) NOT NULL,
                session_id VARCHAR(100) NOT NULL,
                tenant_id VARCHAR(50) NOT NULL,
                from_number VARCHAR(20) NOT NULL,
                to_number VARCHAR(20) NOT NULL,
                issue_type VARCHAR(50),
                severity VARCHAR(20),
                priority_score INTEGER,
                affected_systems JSONB DEFAULT '[]',
                error_messages JSONB DEFAULT '[]',
                user_environment VARCHAR(200),
                steps_to_reproduce TEXT,
                issue_description TEXT,
                status VARCHAR(50) DEFAULT 'open' NOT NULL,
                resolution TEXT,
                kb_articles_used JSONB DEFAULT '[]',
                resolved_at TIMESTAMP,
                jira_ticket_key VARCHAR(100),
                conversation_summary TEXT,
                extra_data JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """))
        
        # Create indexes separately
        indexes = [
            "CREATE INDEX IF NOT EXISTS ix_support_tickets_ticket_id ON support_tickets(ticket_id)",
            "CREATE INDEX IF NOT EXISTS ix_support_tickets_call_sid ON support_tickets(call_sid)",
            "CREATE INDEX IF NOT EXISTS ix_support_tickets_session_id ON support_tickets(session_id)",
            "CREATE INDEX IF NOT EXISTS ix_support_tickets_tenant_id ON support_tickets(tenant_id)",
            "CREATE INDEX IF NOT EXISTS ix_support_tickets_from_number ON support_tickets(from_number)",
            "CREATE INDEX IF NOT EXISTS ix_support_tickets_issue_type ON support_tickets(issue_type)",
            "CREATE INDEX IF NOT EXISTS ix_support_tickets_severity ON support_tickets(severity)",
            "CREATE INDEX IF NOT EXISTS ix_support_tickets_status ON support_tickets(status)",
            "CREATE INDEX IF NOT EXISTS ix_support_tickets_jira_ticket_key ON support_tickets(jira_ticket_key)",
            "CREATE INDEX IF NOT EXISTS ix_support_tickets_created_at ON support_tickets(created_at DESC)",
        ]
        
        for index_sql in indexes:
            await conn.execute(text(index_sql))
    
    await engine.dispose()
    logger.info("Migration completed: support_tickets table created")


if __name__ == "__main__":
    asyncio.run(apply_ticket_migrations())

