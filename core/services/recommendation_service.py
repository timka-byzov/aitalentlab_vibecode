import yaml
import re
from typing import List, Dict, Set
import pymorphy3

from core.domain.curriculum import Course, ProgramCurriculum


class RecommendationService:
    """
    Provides course recommendation and personalized study plan generation.

    This service uses a keyword-based approach with lemmatization to match
    courses against a student's background skills.
    """

    def __init__(
        self, curricula: Dict[str, ProgramCurriculum], config_path: str = "./knowledge_areas.yaml"
    ):
        """
        Initializes the service with program curricula and configuration.

        Args:
            curricula (Dict[str, ProgramCurriculum]): A dictionary mapping program IDs to curriculum objects.
            config_path (str): Path to the YAML configuration file containing knowledge area keywords.
        """
        self.curricula = curricula
        self.morph = pymorphy3.MorphAnalyzer()

        # Load keywords from the external config file
        self.knowledge_areas = self._load_config(config_path)

        # Pre-process keywords into lemmatized sets for efficient matching
        self.lemmatized_areas = {
            area: {self._normalize_word(kw) for kw in keywords}
            for area, keywords in self.knowledge_areas.items()
        }

    def _load_config(self, path: str) -> Dict[str, List[str]]:
        """Loads knowledge areas from a YAML file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config.get("knowledge_areas", {})
        except FileNotFoundError:
            # Handle case where config is missing, you might want to log a warning
            raise FileNotFoundError(f"Config file not found at {path}")


    def _normalize_word(self, word: str) -> str:
        """Converts a word to its base (normal) form."""
        return self.morph.parse(word.lower())[0].normal_form

    def _normalize_text_to_set(self, text: str) -> Set[str]:
        """Normalizes a string of text into a set of its base form words."""
        # Remove punctuation, split into words, and normalize each word
        clean_text = re.sub(r"[^\w\s]", "", text.lower())
        return {self._normalize_word(word) for word in clean_text.split()}

    def recommend_electives(
        self,
        program_id: str,
        background: Dict[str, int],
        max_courses: int = 5,
        strategy: str = "deepen",
    ) -> List[Course]:
        """
        Recommends top electives based on a student's background.

        Args:
            program_id (str): The ID of the master's program.
            background (Dict[str, int]): A dictionary of the user's skills rated from 0 to 5.
            max_courses (int): The maximum number of courses to recommend.
            strategy (str): The recommendation strategy.
                - 'deepen': Recommends courses where the user is already strong.
                - 'broaden': Recommends courses where the user is weak to fill knowledge gaps.

        Returns:
            List[Course]: A sorted list of recommended elective courses.
        """
        program = self.curricula.get(program_id)
        if not program:
            return []

        electives = program.get_electives()

        scored_courses = []
        for course in electives:
            score = 0
            course_words = self._normalize_text_to_set(course.name)

            for area, lemmatized_keywords in self.lemmatized_areas.items():
                # Check for any matching keywords efficiently using set intersection
                if not lemmatized_keywords.isdisjoint(course_words):
                    user_score = background.get(area, 0)
                    if strategy == "deepen":
                        # Reinforce strengths
                        score += user_score
                    elif strategy == "broaden":
                        # Shore up weaknesses (score is higher for weaker areas)
                        score += 5 - user_score
                    else:
                        raise ValueError(f"Unknown recommendation strategy: {strategy}")

            if score > 0:
                scored_courses.append((course, score))

        # Sort by the calculated score in descending order
        scored_courses.sort(key=lambda x: x[1], reverse=True)

        # Return only the course objects from the sorted list
        return [course for course, score in scored_courses][:max_courses]

    def get_study_plan(
        self, program_id: str, background: Dict[str, int], strategy: str = "deepen"
    ) -> Dict[int, List[Course]]:
        """
        Generates a personalized study plan with recommended electives.

        Args:
            program_id (str): The ID of the master's program.
            background (Dict[str, int]): A dictionary of the user's skills.
            strategy (str): The recommendation strategy ('deepen' or 'broaden').

        Returns:
            Dict[int, List[Course]]: A dictionary mapping semester numbers to lists of courses.
        """
        program = self.curricula.get(program_id)
        if not program:
            return {}

        # Get recommended electives for the whole program
        recommended_electives = self.recommend_electives(
            program_id,
            background,
            max_courses=10,
            strategy=strategy,  # Get more to fill semesters
        )

        plan = {}
        for semester in range(1, program.duration_semesters + 1):
            # 1. Start with this semester's compulsory courses
            # ASSUMPTION: Your ProgramCurriculum class has a method to get ONLY compulsory courses.
            semester_courses = program.get_compulsory_courses_by_semester(semester)

            # 2. Add the recommended electives that belong to this semester
            for elective in recommended_electives:
                if elective.semester == semester:
                    semester_courses.append(elective)

            plan[semester] = semester_courses

        return plan
