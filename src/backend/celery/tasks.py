import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from src.backend.celery.celery_app import celery_app
from config import get_settings
import logging
from time import sleep
from datetime import datetime
import asyncio

settings = get_settings()
logger = logging.getLogger("celery.task")

# ============================================================================
# COMPLAINT TASKS
# ============================================================================

@celery_app.task(bind=True, name="tasks.check_complaint_by_id")
def check_complaint_by_id(self, complaint_id: str):
    """Check if a complaint exists by complaint ID"""
    return asyncio.run(_check_complaint_by_id(self, complaint_id))

async def _check_complaint_by_id(self, complaint_id: str):
    import httpx

    url = f"{settings.API_BASE_URL}/complaints/check_by_id/{complaint_id}"
    max_retries = settings.CELERY_TASK_MAX_RETRIES
    retry_delay = settings.CELERY_TASK_RETRY_DELAY

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Successfully checked complaint {complaint_id}: exists={data.get('exists')}")
                return data
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.error(f"Attempt {attempt + 1} failed for complaint_id {complaint_id}: {exc}")
            if attempt < max_retries - 1:
                sleep(retry_delay)
            else:
                logger.error(f"All {max_retries} attempts failed for complaint_id {complaint_id}.")
                raise


@celery_app.task(bind=True, name="tasks.check_complaint_by_order")
def check_complaint_by_order(self, order_id: str):
    """Check if a complaint exists for a given order ID"""
    return asyncio.run(_check_complaint_by_order(self, order_id))

async def _check_complaint_by_order(self, order_id: str):
    import httpx

    url = f"{settings.API_BASE_URL}/complaints/check_by_order/{order_id}"
    max_retries = settings.CELERY_TASK_MAX_RETRIES
    retry_delay = settings.CELERY_TASK_RETRY_DELAY

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Successfully checked complaint for order {order_id}: exists={data.get('exists')}")
                return data
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.error(f"Attempt {attempt + 1} failed for order_id {order_id}: {exc}")
            if attempt < max_retries - 1:
                sleep(retry_delay)
            else:
                logger.error(f"All {max_retries} attempts failed for order_id {order_id}.")
                raise


@celery_app.task(bind=True, name="tasks.create_complaint")
def create_complaint(self, complaint_id: str, order_id: str, issue: str):
    """Create a new complaint asynchronously"""
    return asyncio.run(_create_complaint(self, complaint_id, order_id, issue))

async def _create_complaint(self, complaint_id: str, order_id: str, issue: str):
    import httpx

    url = f"{settings.API_BASE_URL}/complaints"
    payload = {
        "id": complaint_id,
        "order_id": order_id,
        "issue": issue
    }
    max_retries = settings.CELERY_TASK_MAX_RETRIES
    retry_delay = settings.CELERY_TASK_RETRY_DELAY

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Successfully created complaint {complaint_id} for order {order_id}")
                return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400:
                logger.warning(f"Complaint {complaint_id} already exists")
                return {"error": "Complaint already exists", "status_code": 400}
            logger.error(f"Attempt {attempt + 1} failed to create complaint: {exc}")
            if attempt < max_retries - 1:
                sleep(retry_delay)
            else:
                raise
        except httpx.RequestError as exc:
            logger.error(f"Attempt {attempt + 1} failed with request error: {exc}")
            if attempt < max_retries - 1:
                sleep(retry_delay)
            else:
                raise


@celery_app.task(bind=True, name="tasks.get_complaint_details")
def get_complaint_details(self, complaint_id: str):
    """Get full complaint details by ID"""
    return asyncio.run(_get_complaint_details(self, complaint_id))

async def _get_complaint_details(self, complaint_id: str):
    import httpx

    url = f"{settings.API_BASE_URL}/complaints/{complaint_id}"
    max_retries = settings.CELERY_TASK_MAX_RETRIES
    retry_delay = settings.CELERY_TASK_RETRY_DELAY

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Successfully retrieved complaint details for {complaint_id}")
                return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.warning(f"Complaint {complaint_id} not found")
                return {"error": "Complaint not found", "status_code": 404}
            logger.error(f"Attempt {attempt + 1} failed: {exc}")
            if attempt < max_retries - 1:
                sleep(retry_delay)
            else:
                raise
        except httpx.RequestError as exc:
            logger.error(f"Attempt {attempt + 1} failed with request error: {exc}")
            if attempt < max_retries - 1:
                sleep(retry_delay)
            else:
                raise


# ============================================================================
# ORDER TASKS
# ============================================================================

@celery_app.task(bind=True, name="tasks.get_order_status")
def get_order_status(self, order_id: str):
    """Get order status and delivery information"""
    return asyncio.run(_get_order_status(self, order_id))

async def _get_order_status(self, order_id: str):
    import httpx

    url = f"{settings.API_BASE_URL}/orders/{order_id}"
    max_retries = settings.CELERY_TASK_MAX_RETRIES
    retry_delay = settings.CELERY_TASK_RETRY_DELAY

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Successfully retrieved order status for {order_id}: {data.get('status')}")
                return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.warning(f"Order {order_id} not found")
                return {"error": "Order not found", "status_code": 404}
            logger.error(f"Attempt {attempt + 1} failed: {exc}")
            if attempt < max_retries - 1:
                sleep(retry_delay)
            else:
                raise
        except httpx.RequestError as exc:
            logger.error(f"Attempt {attempt + 1} failed with request error: {exc}")
            if attempt < max_retries - 1:
                sleep(retry_delay)
            else:
                raise


# ============================================================================
# ESCALATION TASKS
# ============================================================================

@celery_app.task(bind=True, name="tasks.escalate_complaint")
def escalate_complaint(self, complaint_id: str):
    """Escalate a complaint to higher support level"""
    return asyncio.run(_escalate_complaint(self, complaint_id))

async def _escalate_complaint(self, complaint_id: str):
    import httpx

    url = f"{settings.API_BASE_URL}/escalations"
    payload = {"complaint_id": complaint_id}
    max_retries = settings.CELERY_TASK_MAX_RETRIES
    retry_delay = settings.CELERY_TASK_RETRY_DELAY

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Successfully escalated complaint {complaint_id}: escalation_id={data.get('escalation_id')}")
                return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.warning(f"Complaint {complaint_id} not found for escalation")
                return {"error": "Complaint not found", "status_code": 404}
            logger.error(f"Attempt {attempt + 1} failed to escalate: {exc}")
            if attempt < max_retries - 1:
                sleep(retry_delay)
            else:
                raise
        except httpx.RequestError as exc:
            logger.error(f"Attempt {attempt + 1} failed with request error: {exc}")
            if attempt < max_retries - 1:
                sleep(retry_delay)
            else:
                raise


# ============================================================================
# BACKGROUND PROCESSING TASKS
# ============================================================================

@celery_app.task(bind=True, name="tasks.process_complaint_workflow")
def process_complaint_workflow(self, order_id: str, issue: str, complaint_id: str = None):
    """
    Complete workflow: Check order -> Create complaint -> Auto-escalate if critical
    """
    return asyncio.run(_process_complaint_workflow(self, order_id, issue, complaint_id))

async def _process_complaint_workflow(self, order_id: str, issue: str, complaint_id: str = None):
    import httpx
    from uuid import uuid4

    if not complaint_id:
        complaint_id = str(uuid4())

    workflow_result = {
        "order_id": order_id,
        "complaint_id": complaint_id,
        "steps": []
    }

    # Step 1: Check order exists
    logger.info(f"Step 1: Checking order {order_id}")
    try:
        order_result = await _get_order_status(self, order_id)
        if "error" in order_result:
            workflow_result["steps"].append({"step": "check_order", "status": "failed", "error": order_result["error"]})
            return workflow_result
        workflow_result["steps"].append({"step": "check_order", "status": "success", "order": order_result})
    except Exception as e:
        workflow_result["steps"].append({"step": "check_order", "status": "failed", "error": str(e)})
        return workflow_result

    # Step 2: Create complaint
    logger.info(f"Step 2: Creating complaint {complaint_id}")
    try:
        complaint_result = await _create_complaint(self, complaint_id, order_id, issue)
        if "error" in complaint_result:
            workflow_result["steps"].append({"step": "create_complaint", "status": "failed", "error": complaint_result["error"]})
            return workflow_result
        workflow_result["steps"].append({"step": "create_complaint", "status": "success", "complaint": complaint_result})
    except Exception as e:
        workflow_result["steps"].append({"step": "create_complaint", "status": "failed", "error": str(e)})
        return workflow_result

    # Step 3: Auto-escalate if issue contains critical keywords
    critical_keywords = ["damaged", "lost", "wrong item", "missing", "urgent", "critical"]
    should_escalate = any(keyword in issue.lower() for keyword in critical_keywords)

    if should_escalate:
        logger.info(f"Step 3: Auto-escalating complaint {complaint_id} due to critical issue")
        try:
            escalation_result = await _escalate_complaint(self, complaint_id)
            workflow_result["steps"].append({"step": "auto_escalate", "status": "success", "escalation": escalation_result})
        except Exception as e:
            workflow_result["steps"].append({"step": "auto_escalate", "status": "failed", "error": str(e)})
    else:
        workflow_result["steps"].append({"step": "auto_escalate", "status": "skipped", "reason": "Not a critical issue"})

    workflow_result["completed"] = True
    logger.info(f"Workflow completed for complaint {complaint_id}")
    return workflow_result


@celery_app.task(bind=True, name="tasks.send_notification")
def send_notification(self, recipient: str, message_type: str, data: dict):
    """
    Send notification (email/SMS) - mock implementation
    In production, integrate with email service (SendGrid, AWS SES) or SMS (Twilio)
    """
    logger.info(f"Sending {message_type} notification to {recipient}")
    logger.info(f"Notification data: {data}")
    
    # Mock notification sending
    notification_result = {
        "recipient": recipient,
        "message_type": message_type,
        "data": data,
        "sent_at": datetime.utcnow().isoformat(),
        "status": "sent",
        "message": f"{message_type} notification sent successfully"
    }
    
    sleep(2)  # Simulate network delay
    logger.info(f"Notification sent to {recipient}")
    return notification_result


@celery_app.task(bind=True, name="tasks.generate_daily_report")
def generate_daily_report(self):
    """
    Generate daily summary report of complaints and escalations
    This would typically run on a schedule (Celery Beat)
    """
    logger.info("Generating daily report...")
    
    # Mock report generation
    report = {
        "date": datetime.utcnow().date().isoformat(),
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_complaints": 0,
            "escalated_complaints": 0,
            "resolved_complaints": 0,
            "pending_complaints": 0
        },
        "status": "generated"
    }
    
    sleep(3)  # Simulate report generation
    logger.info("Daily report generated successfully")
    return report


# ============================================================================
# BATCH PROCESSING TASKS
# ============================================================================

@celery_app.task(bind=True, name="tasks.batch_check_orders")
def batch_check_orders(self, order_ids: list):
    """Check status of multiple orders in batch"""
    return asyncio.run(_batch_check_orders(self, order_ids))

async def _batch_check_orders(self, order_ids: list):
    import httpx
    
    results = []
    async with httpx.AsyncClient() as client:
        for order_id in order_ids:
            try:
                result = await _get_order_status(self, order_id)
                results.append({"order_id": order_id, "status": "success", "data": result})
            except Exception as e:
                results.append({"order_id": order_id, "status": "failed", "error": str(e)})
    
    logger.info(f"Batch processed {len(order_ids)} orders")
    return {
        "total": len(order_ids),
        "results": results
    }
