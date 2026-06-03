"""Deprecated multi-student seed — use reset_school_single_student instead."""
import asyncio
from app.microservices.school.reset_school_single_student import reset_school_data

if __name__ == "__main__":
    asyncio.run(reset_school_data())
