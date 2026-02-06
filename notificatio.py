from sqlalchemy import select

from app.db.models.interviews import Interviews
from app.db.models.candidates import Candidates
from app.services.email_generator import send_email


async def send_interview_email(interview_id: str, db):
    # Fetch interview
    interview_result = await db.execute(
        select(Interviews).where(Interviews.id == interview_id)
    )
    interview = interview_result.scalar_one()

    # Fetch candidate details using candidate_id
    candidate_result = await db.execute(
        select(Candidates).where(Candidates.id == interview.candidate_id)
    )
    candidate = candidate_result.scalar_one()

    email_payload = {
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "reciever_email": candidate.email,
        "interview_date": interview.start_time.isoformat() if interview.start_time else "",
        "poc_name": "Recruitment Team",
        "poc_email": "recruitment@hexaware.com",
    }

    send_email(email_payload)
