import re
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Booking
from app.schemas import BookingInfo

BOOKING_INTENT_KEYWORDS = ["book", "interview", "schedule", "appointment", "meeting"]


def detect_booking_intent(text: str) -> bool:
    normalized = text.lower()
    return any(keyword in normalized for keyword in BOOKING_INTENT_KEYWORDS)


async def save_booking_info(answer_text: str, db: AsyncSession) -> BookingInfo | None:
    pattern = re.compile(
        r"name\s*[:\-]?\s*(?P<name>[A-Za-z ]+).*?email\s*[:\-]?\s*(?P<email>[\w.@+-]+).*?date\s*[:\-]?\s*(?P<date>\d{4}-\d{2}-\d{2}).*?time\s*[:\-]?\s*(?P<time>[0-2]?\d:[0-5]\d)",
        re.IGNORECASE | re.DOTALL,
    )

    match = pattern.search(answer_text)
    if not match:
        return None

    booking = Booking(
        name=match.group("name").strip(),
        email=match.group("email").strip(),
        date=datetime.fromisoformat(match.group("date")),
        time=match.group("time").strip(),
    )
    db.add(booking)
    await db.commit()
    return BookingInfo(
        name=booking.name,
        email=booking.email,
        date=booking.date,
        time=booking.time,
    )
