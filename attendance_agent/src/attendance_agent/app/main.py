from attendance_agent.agent import (
    AttendanceAgent,
)

from attendance_agent.attendance import (
    AttendanceService,
)

from attendance_agent.logger import logger


def main():
    """
    Start the attendance agent CLI.
    """

    # -----------------------------------------
    # Student configuration
    # -----------------------------------------

    student_name = "demo"

    student_email = (
        "demo@gmail.com"
    )

    college_id = 1

    classroom_id = 6

    # -----------------------------------------
    # Start
    # -----------------------------------------

    logger.info(
        "Starting Attendance Agent"
    )

    service = (
        AttendanceService()
    )

    # -----------------------------------------
    # Fetch attendance
    # -----------------------------------------

    attendance_data = (
        service.get_attendance(
            student_name=student_name,
            student_email=student_email,
            college_id=college_id,
            classroom_id=classroom_id,
        )
    )

    if not attendance_data.get(
        "success"
    ):

        print(
            attendance_data.get(
                "message",
                "Failed to fetch attendance.",
            )
        )

        return

    # -----------------------------------------
    # Display summary
    # -----------------------------------------

    summary = (
        attendance_data[
            "summary"
        ]
    )

    print()

    print("=" * 60)

    print(
        "                 ATTENDANCE AGENT"
    )

    print("=" * 60)

    print(
        f"Student : "
        f"{attendance_data['student']['name']}"
    )

    print(
        f"PRN     : "
        f"{attendance_data['student']['prn']}"
    )

    print(
        f"Class   : "
        f"{attendance_data['classroom_name']}"
    )

    print(
        f"Attendance : "
        f"{summary['attendance_percentage']}%"
    )

    print(
        f"Present : {summary['present']} | "
        f"Absent : {summary['absent']} | "
        f"Pending : {summary['pending']}"
    )

    print("=" * 60)

    # -----------------------------------------
    # Create agent
    # -----------------------------------------

    agent = AttendanceAgent(
        attendance_data=attendance_data,
        session_id="attendance-cli",
    )

    # -----------------------------------------
    # Chat loop
    # -----------------------------------------

    while True:

        try:

            question = input(
                "\nYou >> "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError,
        ):

            print(
                "\nGoodbye!"
            )

            break

        if question.lower() in {
            "exit",
            "quit",
        }:

            print(
                "Goodbye!"
            )

            break

        if not question:
            continue

        answer = agent.ask(
            question
        )

        print(
            "\nAssistant:",
            answer,
        )


if __name__ == "__main__":
    main()