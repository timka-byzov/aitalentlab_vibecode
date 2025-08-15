from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Course:
    """Represents a single course within a curriculum."""

    id: str
    name: str
    semester: int
    credits: int
    is_compulsory: bool
    prerequisites: List[str]
    description: Optional[str] = None
    workload_hours: int = 0


@dataclass
class ProgramCurriculum:
    """
    Represents the entire curriculum for a master's program, including all courses
    and metadata about the program.
    """

    program_name: str
    courses: List[Course]
    total_credits: int
    duration_semesters: int

    def get_electives(self) -> List[Course]:
        """Returns a list of all elective courses in the program."""
        return [course for course in self.courses if not course.is_compulsory]

    def get_courses_by_semester(self, semester: int) -> List[Course]:
        """Returns a list of all courses offered in a specific semester."""
        return [course for course in self.courses if course.semester == semester]

    def get_compulsory_courses_by_semester(self, semester: int) -> List[Course]:
        """
        Returns a list of compulsory courses for a specific semester.
        """
        return [
            course
            for course in self.courses
            if course.is_compulsory and course.semester == semester
        ]

    def get_electives_by_semester(self, semester: int) -> List[Course]:
        """Returns a list of elective courses for a specific semester."""
        return [
            course
            for course in self.courses
            if not course.is_compulsory and course.semester == semester
        ]

    def find_course_by_id(self, course_id: str) -> Optional[Course]:
        """
        Finds a single course by its unique ID.

        Returns:
            The Course object if found, otherwise None.
        """
        for course in self.courses:
            if course.id == course_id:
                return course
        return None

    def get_semester_credits(self, semester: int) -> int:
        """Calculates the total number of credits for all courses in a given semester."""
        courses_in_semester = self.get_courses_by_semester(semester)
        return sum(course.credits for course in courses_in_semester)

    def get_semester_workload(self, semester: int) -> int:
        """Calculates the total workload in hours for all courses in a given semester."""
        courses_in_semester = self.get_courses_by_semester(semester)
        return sum(course.workload_hours for course in courses_in_semester)
