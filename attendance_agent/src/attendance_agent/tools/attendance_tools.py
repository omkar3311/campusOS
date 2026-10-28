from datetime import datetime

from langchain_core.tools import tool

from attendance_agent.logger import logger


def create_attendance_tools(
    data: dict,
):
    """
    Create attendance-specific tools.

    The tools operate only on the attendance data
    already fetched for the student.
    """

    @tool
    def get_attendance_for_date(
        date_str: str,
    ) -> dict:
        """
        Get attendance information for exactly one date.

        Date format:
        YYYY-MM-DD

        Use this tool for questions about:

        - present or absent status
        - specific slots
        - teachers
        - audit history
        - attendance on a specific date

        Call this tool only once for the same date
        during a single request.
        """

        logger.info(
            "Tool: get_attendance_for_date | "
            "date=%s",
            date_str,
        )

        attendance = data.get(
            "attendance",
            {},
        )

        record = attendance.get(
            date_str
        )

        if not record:
            return {
                "found": False,
                "message": (
                    f"No attendance record "
                    f"found for {date_str}"
                ),
            }

        return {
            "found": True,
            "date": date_str,
            "slots": record[
                "slots"
            ],
            "audit": record.get(
                "audit",
                [],
            ),
        }

    @tool
    def get_attendance_for_month(
        year: int,
        month: int,
    ) -> dict:
        """
        Get attendance records for a specific
        year and month.

        Example:

        year=2026
        month=3
        """

        logger.info(
            "Tool: get_attendance_for_month | "
            "year=%s | month=%s",
            year,
            month,
        )

        attendance = data.get(
            "attendance",
            {},
        )

        result = {}

        for date_str, record in attendance.items():

            try:
                dt = datetime.strptime(
                    date_str,
                    "%Y-%m-%d",
                )

            except ValueError:
                continue

            if (
                dt.year == year
                and dt.month == month
            ):
                result[
                    date_str
                ] = record

        return result

    return [
        get_attendance_for_date,
        get_attendance_for_month,
    ]