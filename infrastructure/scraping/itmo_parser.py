import re
from io import BytesIO
from typing import Dict, List

import PyPDF2
import requests
from bs4 import BeautifulSoup

from core.domain.curriculum import Course, ProgramCurriculum


class ItmoParser:
    BASE_URL = "https://abit.itmo.ru"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def parse_program(self, program_url: str, program_name: str) -> ProgramCurriculum:
        """Parse curriculum from program page"""
        response = self.session.get(program_url)
        response.raise_for_status()

        # Find academic_plan URL from JSON data
        academic_plan_pattern = r'"academic_plan"\s*:\s*"([^"]+)"'
        match = re.search(academic_plan_pattern, response.text)
        if not match:
            raise ValueError(f"Academic plan URL not found at {program_url}")

        pdf_url = match.group(1)
        pdf_response = self.session.get(pdf_url)
        pdf_response.raise_for_status()

        return self.parse_pdf_curriculum(
            pdf_content=pdf_response.content,
            program_name=program_name,
        )

    def parse_pdf_curriculum(
        self, pdf_content: bytes, program_name: str
    ) -> ProgramCurriculum:
        """Parse curriculum from PDF content"""
        courses = []
        pdf_file = BytesIO(pdf_content)
        reader = PyPDF2.PdfReader(pdf_file)

        # Extract text from all pages
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"

        # Split text into lines
        lines = full_text.split("\n")
        current_semester = None
        current_category = None
        courses = []

        for line in lines:
            line = line.strip()

            # Detect program name
            if "ОП" in line:
                program_match = re.search(r"ОП\s+(.+)", line)
                if program_match:
                    program_name = program_match.group(1).strip()

            # Detect semester
            semester_match = re.search(r"(\d+)\s+семестр", line)
            if semester_match:
                current_semester = int(semester_match.group(1))

            # Detect category (compulsory/elective)
            if "Обязательные" in line:
                current_category = "compulsory"
            elif "Пул выборных" in line or "Выборные" in line:
                current_category = "elective"

            # Parse course lines
            if current_semester and current_category:
                # Match lines like: "1Воркшоп по созданию продукта на данных / Data Product Development Workshop 3108"
                course_match = re.search(r"^(\d+)([^\d].+?)\s+(\d+)$", line)
                if course_match:
                    course_code = course_match.group(1)
                    course_name = course_match.group(2).strip()
                    # hours = int(course_match.group(3))  # Not currently used

                    # Extract workload hours
                    workload_hours = int(course_match.group(3))

                    courses.append(
                        Course(
                            id=course_code,
                            name=course_name,
                            semester=current_semester,
                            credits=0,  # Credits not available in this format
                            is_compulsory=(current_category == "compulsory"),
                            prerequisites=[],
                            workload_hours=workload_hours,
                        )
                    )

        if not courses:
            raise ValueError("No courses found in PDF curriculum")

        return ProgramCurriculum(
            program_name=program_name,
            courses=courses,
            total_credits=0,  # Total credits not available in this format
            duration_semesters=max(c.semester for c in courses) if courses else 0,
        )

    def get_all_programs(self) -> Dict[str, ProgramCurriculum]:
        """Parse both AI programs"""
        return {
            "ai": self.parse_program("https://abit.itmo.ru/program/master/ai", "AI"),
            "ai_product": self.parse_program(
                "https://abit.itmo.ru/program/master/ai_product", "AI Product"
            ),
        }
