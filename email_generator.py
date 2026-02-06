import sys
import os
import asyncio
from concurrent.futures import TimeoutError as FuturesTimeoutError

# Add both parent and grandparent directories to path for imports to work when run separately
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(current_dir, "../")))      # /backend/app
sys.path.append(os.path.abspath(os.path.join(current_dir, "../../")))   # /backend

from utils.logger_setup import logger
from utils.config_setup import cfg

from azure.communication.email import EmailClient
from azure.core.exceptions import HttpResponseError, ServiceRequestError

# ---------------------------------------------------------
# Config
# ---------------------------------------------------------
EMAIL_CFG = cfg["email_config"]
FRONTEND_APP_URL = cfg["email_config"]["frontend"]["app_url"]

SENDER = EMAIL_CFG["AZURE_COMMUNICATION_MAIL"]

EMAIL_CONNECTION_STRING = (
    f"endpoint={EMAIL_CFG['AZURE_COMMUNICATION_ENDPOINT']};"
    f"accesskey={EMAIL_CFG['AZURE_COMMUNICATION_ACCESS_KEY']}"
)


# ---------------------------------------------------------
# Email Client (created once)
# ---------------------------------------------------------
email_client = EmailClient.from_connection_string(
    EMAIL_CONNECTION_STRING
)


# ---------------------------------------------------------
# Email Sender
# ---------------------------------------------------------
def send_email(email_parameters: dict) -> bool:
    """
    Sends interview scheduled email to candidate with interview details
    """

    try:
        first_name = email_parameters["first_name"]
        last_name = email_parameters["last_name"]
        receiver_email = email_parameters["reciever_email"]
        interview_date = email_parameters["interview_date"]
        interview_id = email_parameters.get("interview_id", "N/A")
        job_role = email_parameters.get("job_role", "Position")
        duration = email_parameters.get("duration", "N/A")
        interview_link = email_parameters.get("interview_link", FRONTEND_APP_URL)
        poc_username = email_parameters.get("poc_name")
        poc_email = email_parameters.get("poc_email")

        subject = f"Interview Scheduled - {job_role}"

        logger.info(
            "Sending interview email",
            extra={
                "to": receiver_email,
                "interview_id": interview_id,
                "job_role": job_role
            }
        )

        message = {
            "senderAddress": SENDER,
            "recipients": {
                "to": [{"address": receiver_email}],
            },
            "content": {
                "subject": subject,
                "plainText": (
                    f"Hello {first_name} {last_name},\n\n"
                    f"Your interview has been successfully scheduled.\n\n"
                    f"Interview Details:\n"
                    f"- Position: {job_role}\n"
                    f"- Date & Time: {interview_date}\n"
                    f"- Duration: {duration} minutes\n"
                    f"- Interview ID: {interview_id}\n\n"
                    f"Please click the link below to access your interview:\n"
                    f"{interview_link}\n\n"
                    f"For any queries, contact {poc_username or 'Recruitment Team'}.\n\n"
                    f"Best regards,\n"
                    f"AI Talent Quest Team\n"
                    f"Hexaware Technologies"
                ),
                "html": email_html(
                    subject=subject,
                    first_name=first_name,
                    last_name=last_name,
                    interview_date=interview_date,
                    interview_id=interview_id,
                    job_role=job_role,
                    duration=duration,
                    interview_link=interview_link,
                    poc_username=poc_username,
                    poc_email=poc_email,
                ),
            },
        }

        logger.info(
            "Initiating email send via Azure Communication Service",
            extra={
                "to": receiver_email,
                "interview_id": interview_id,
                "sender": SENDER,
                "endpoint": EMAIL_CFG['AZURE_COMMUNICATION_ENDPOINT'][:50] + "..."
            }
        )
        
        try:
            poller = email_client.begin_send(message)
            try:
                # wait max 20 seconds
                result = poller.result(timeout=20)
            except Exception as exc:
                logger.error(f"EMAIL | timeout or failure: {exc}")
                return False
            
            logger.info(
                "Email send request submitted, waiting for result (timeout: 30s)...",
                extra={"interview_id": interview_id}
            )
            
            # Wait for result with timeout
            result = poller.result(timeout=30)

            logger.info(
                "✅ Email sent successfully",
                extra={
                    "to": receiver_email,
                    "message_id": result.get("id") if result else "N/A",
                    "status": result.get("status") if result else "N/A",
                    "interview_id": interview_id,
                },
            )
            return True
            
        except FuturesTimeoutError:
            logger.error(
                "Email send timeout (30s) - Azure Communication Service not responding",
                extra={
                    "to": receiver_email,
                    "interview_id": interview_id,
                    "endpoint": EMAIL_CFG['AZURE_COMMUNICATION_ENDPOINT']
                }
            )
            return False

    except HttpResponseError as e:
        logger.error(
            "❌ Azure email send failed - HTTP Error",
            extra={
                "to": receiver_email,
                "status_code": e.status_code,
                "error_code": e.error.code if e.error else None,
                "error_message": e.message,  # Changed from "message" to avoid logging conflict
                "endpoint": EMAIL_CFG['AZURE_COMMUNICATION_ENDPOINT'],
                "interview_id": interview_id,
            },
        )
        return False

    except ServiceRequestError as e:
        logger.error(
            "❌ Network error while sending email - Cannot reach Azure Communication Service",
            extra={
                "to": receiver_email,
                "error": str(e),
                "endpoint": EMAIL_CFG['AZURE_COMMUNICATION_ENDPOINT'],
                "interview_id": interview_id,
            },
            exc_info=True
        )
        return False

    except Exception as e:
        logger.exception(
            "❌ Unexpected error while sending email",
            extra={
                "to": receiver_email,
                "error": str(e),
                "error_type": type(e).__name__,
                "endpoint": EMAIL_CFG['AZURE_COMMUNICATION_ENDPOINT'],
                "interview_id": interview_id,
            },
        )
        return False


# ---------------------------------------------------------
# HTML Template
# ---------------------------------------------------------
def email_html(
    subject: str,
    first_name: str,
    last_name: str,
    interview_date: str,
    interview_id: str,
    job_role: str,
    duration: str,
    interview_link: str,
    poc_username: str | None = None,
    poc_email: str | None = None,
) -> str:
    poc_info = f"For any queries, please contact {poc_username or 'the Recruitment Team'}"
    if poc_email:
        poc_info += f" at {poc_email}"

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee;">
            <h2 style="color: #667eea;">Interview Invitation - AI Talent Quest</h2>
            
            <p>Hello {first_name} {last_name},</p>
            
            <p>Your interview has been successfully scheduled. Please find the details below:</p>
            
            <p style="background-color: #f9f9f9; padding: 15px; border-radius: 5px;">
                <strong>Position:</strong> {job_role}<br>
                <strong>Date & Time:</strong> {interview_date}<br>
                <strong>Duration:</strong> {duration} minutes<br>
                <strong>Interview ID:</strong> {interview_id}
            </p>
            
            <p>To access your interview, please click the link below (you will be asked to log in first):</p>
            
            <p style="margin: 30px 0;">
                <a href="{interview_link}" style="background-color: #667eea; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">START INTERVIEW</a>
            </p>
            
            <p style="font-size: 14px; color: #666;">
                Direct link: <a href="{interview_link}">{interview_link}</a>
            </p>
            
            <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
            
            <p style="font-size: 14px; color: #666;">
                {poc_info}.<br><br>
                Best regards,<br>
                <strong>AI Talent Quest Team</strong><br>
                Hexaware Technologies
            </p>
        </div>
    </body>
    </html>
    """


# ---------------------------------------------------------
# Local Test
# ---------------------------------------------------------
dummy_email_parameters = {
    "first_name": "Yazhini",
    "last_name": "S",
    "reciever_email": "JagasriB@hexaware.com",
    "interview_date": "25 Dec 2025, 12:30 PM IST",
    "poc_name": "HR Team",
    "poc_email": "hr@hexaware.com",
}


if __name__ == "__main__":
    success = send_email(dummy_email_parameters)

    if success:
        print("Dummy interview email sent successfully")
    else:
        print("Failed to send dummy interview email")
