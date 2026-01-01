"""Test Jira connection and configuration."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.jira_service import jira_service
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


async def test_jira_connection():
    """Test Jira connection and create a test ticket."""
    print("=" * 60)
    print("Jira Connection Test")
    print("=" * 60)
    print()

    # Check configuration
    print("1. Checking configuration...")
    if not settings.JIRA_SERVER:
        print("   ❌ JIRA_SERVER not set")
        return False
    else:
        print(f"   ✓ JIRA_SERVER: {settings.JIRA_SERVER}")

    if not settings.JIRA_EMAIL:
        print("   ❌ JIRA_EMAIL not set")
        return False
    else:
        print(f"   ✓ JIRA_EMAIL: {settings.JIRA_EMAIL}")

    if not settings.JIRA_API_TOKEN:
        print("   ❌ JIRA_API_TOKEN not set")
        return False
    else:
        masked_token = settings.JIRA_API_TOKEN[:10] + "..." + settings.JIRA_API_TOKEN[-10:]
        print(f"   ✓ JIRA_API_TOKEN: {masked_token}")

    if not settings.JIRA_PROJECT_KEY:
        print("   ❌ JIRA_PROJECT_KEY not set")
        return False
    else:
        print(f"   ✓ JIRA_PROJECT_KEY: {settings.JIRA_PROJECT_KEY}")

    print()

    # Test connection
    print("2. Testing connection to Jira...")
    try:
        connected = await jira_service._ensure_connected()
        if connected:
            print("   ✓ Successfully connected to Jira!")
        else:
            print("   ❌ Failed to connect to Jira")
            print("   Check your credentials and server URL")
            return False
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        print("   Common issues:")
        print("   - Incorrect server URL (should be https://company.atlassian.net)")
        print("   - Wrong email address")
        print("   - Invalid or expired API token")
        return False

    print()

    # Test project access
    print(f"3. Testing access to project '{settings.JIRA_PROJECT_KEY}'...")
    try:
        # Try to get project info (this will fail if project doesn't exist)
        loop = asyncio.get_event_loop()
        from concurrent.futures import ThreadPoolExecutor
        executor = ThreadPoolExecutor(max_workers=1)
        
        project = await loop.run_in_executor(
            executor,
            lambda: jira_service.client.project(settings.JIRA_PROJECT_KEY),
        )
        print(f"   ✓ Project found: {project.name} (Key: {project.key})")
    except Exception as e:
        print(f"   ❌ Cannot access project: {e}")
        print(f"   Make sure project key '{settings.JIRA_PROJECT_KEY}' exists and you have access")
        return False

    print()

    # Test ticket creation (optional)
    print("4. Testing ticket creation...")
    try:
        response = input("   Create a test ticket? (y/n): ").strip().lower()
    except EOFError:
        # Non-interactive mode (e.g., Docker)
        print("   Skipping test ticket creation (non-interactive mode)")
        response = "n"
    
    if response == "y":
        try:
            test_ticket_key = await jira_service.create_ticket(
                summary="[TEST] IT Support Bot - Connection Test",
                description="This is a test ticket created by the IT Support Bot to verify Jira integration.",
                issue_type="Task",
                priority="Low",
                labels=["test", "automation"],
            )
            print(f"   ✓ Test ticket created: {test_ticket_key}")
            print(f"   View it at: {settings.JIRA_SERVER}/browse/{test_ticket_key}")
        except Exception as e:
            print(f"   ❌ Failed to create test ticket: {e}")
            return False
    else:
        print("   Skipping test ticket creation")

    print()
    print("=" * 60)
    print("✅ All tests passed! Jira is configured correctly.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_jira_connection())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

