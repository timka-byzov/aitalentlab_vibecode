import logging
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    PicklePersistence,
)
from core.services.recommendation_service import RecommendationService
from infrastructure.scraping.itmo_parser import ItmoParser

PROGRAM, BACKGROUND, QUESTIONS = range(3)

PROGRAM_MAP = {
    "Искусственный интеллект": "ai",
    "Продуктовая разработка на основе ИИ": "ai_product",
}


class AdmissionBot:
    def __init__(self, curricula: dict, recommender: RecommendationService):
        self.curricula = curricula
        self.recommender = recommender

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not update.effective_message:
            return ConversationHandler.END

        reply_keyboard = [list(PROGRAM_MAP.keys())]
        await update.effective_message.reply_text(
            "Привет! Я помогу тебе выбрать магистерскую программу и составить учебный план.\n\n"
            "Пожалуйста, выбери программу, которая тебя интересует:",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=True,
                resize_keyboard=True,
                input_field_placeholder="Выберите программу",
            ),
        )
        return PROGRAM

    async def program_selected(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if not update.effective_message or not update.effective_message.text:
            return ConversationHandler.END

        user_choice = update.effective_message.text
        if user_choice not in PROGRAM_MAP:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "Пожалуйста, выберите программу, используя предложенные кнопки."
                )
            return PROGRAM

        # Ensure chat_data is initialized
        if context.chat_data is None:
            context.chat_data = {}

        context.chat_data["program_name"] = user_choice
        context.chat_data["program_id"] = PROGRAM_MAP[user_choice]

        if update.effective_message:
            await update.effective_message.reply_text(
                "Отлично! Теперь расскажи о своём бэкграунде в следующих областях (оцени от 0 до 5):\n"
                "• Математика\n"
                "• Программирование\n"
                "• Искусственный интеллект\n"
                "• Работа с данными\n"
                "• Продуктовая разработка\n\n"
                "Отправь 5 чисел через пробел. Например: 4 3 2 3 1",
                reply_markup=ReplyKeyboardRemove(),
            )
        return BACKGROUND

    async def background_received(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        try:
            if not update.effective_message or not update.effective_message.text:
                return ConversationHandler.END

            try:
                scores = list(map(int, update.effective_message.text.split()))
                if len(scores) != 5 or not all(0 <= score <= 5 for score in scores):
                    raise ValueError("Некорректное количество чисел или диапазон.")
            except ValueError:
                if update.effective_message:
                    await update.effective_message.reply_text(
                        "Ошибка! Пожалуйста, введи 5 чисел от 0 до 5 через пробел (например: 4 3 2 3 1)."
                    )
                return BACKGROUND

            background = {
                "math": scores[0],
                "programming": scores[1],
                "ai": scores[2],
                "data": scores[3],
                "product": scores[4],
            }
            context.chat_data["background"] = background

            program_name = context.chat_data["program_name"]
            program_id = context.chat_data["program_id"]

            # Get recommended electives only
            recommended = self.recommender.recommend_electives(program_id, background)

            if not recommended:
                if update.effective_message:
                    await update.effective_message.reply_text(
                        "Не удалось подобрать курсы по вашему бэкграунду."
                    )
                return ConversationHandler.END

            # Group by semester
            plan = {}
            for course in recommended:
                if course.semester not in plan:
                    plan[course.semester] = []
                plan[course.semester].append(course)

            if update.effective_message:
                await update.effective_message.reply_text(
                    f"Отлично! Вот рекомендованные курсы для «{program_name}»:"
                )

            # Send each semester's courses in a separate message
            if update.effective_message:
                for semester, courses in plan.items():
                    semester_lines = [f"Семестр {semester}:"]
                    for course in courses:
                        semester_lines.append(f"• {course.name} (выборный)")
                    await update.effective_message.reply_text("\n".join(semester_lines))

            await update.effective_message.reply_text(
                "Теперь ты можешь задавать вопросы по программе. Например:\n"
                "• Какие обязательные курсы в первом семестре?"
            )
            return QUESTIONS

        except Exception as e:
            if update.effective_user:
                logging.error(
                    f"Ошибка при генерации учебного плана для user_id {update.effective_user.id}:",
                    exc_info=True,
                )
            if update.effective_message:
                await update.effective_message.reply_text(
                    "Произошла внутренняя ошибка при составлении плана. "
                    "Мы уже работаем над этим. Пожалуйста, попробуйте начать заново: /start"
                )
            return ConversationHandler.END

    async def answer_question(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if not update.effective_message or not update.effective_message.text:
            return ConversationHandler.END

        # Ensure chat_data is initialized
        if context.chat_data is None:
            context.chat_data = {}

        # Check if program data exists
        if "program_id" not in context.chat_data:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "Программа не выбрана. Пожалуйста, начните заново с /start"
                )
            return ConversationHandler.END

        question = update.effective_message.text.lower()
        program_id = context.chat_data["program_id"]

        if not program_id:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "Что-то пошло не так. Пожалуйста, начни заново с /start"
                )
            return ConversationHandler.END

        program = self.curricula.get(program_id)
        if not program:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "Программа не найдена. Пожалуйста, начните заново с /start"
                )
            return ConversationHandler.END

        if "обязательные" in question and "семестр" in question:
            semester = (
                1
                if "первый" in question or "1" in question
                else 2 if "второй" in question or "2" in question else None
            )
            if semester:
                courses = [
                    c.name
                    for c in program.courses
                    if c.semester == semester and c.is_compulsory
                ]
                response = (
                    f"Обязательные курсы в {semester} семестре:\n• "
                    + "\n• ".join(courses)
                    if courses
                    else f"Не найдено обязательных курсов в {semester} семестре."
                )
                if update.effective_message:
                    await update.effective_message.reply_text(response)
                return QUESTIONS

        if update.effective_message:
            await update.effective_message.reply_text(
                "Я пока учусь отвечать на вопросы. Попробуй спросить что-то вроде 'Какие обязательные курсы в первом семестре?'"
            )
        return QUESTIONS

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # Clear chat_data if it exists
        if context.chat_data is not None:
            context.chat_data.clear()

        if update.effective_message:
            await update.effective_message.reply_text(
                "Диалог завершён. Если захочешь начать заново, просто напиши /start.",
                reply_markup=ReplyKeyboardRemove(),
            )
        return ConversationHandler.END


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Не установлена переменная окружения TELEGRAM_BOT_TOKEN")

    persistence = PicklePersistence(filepath="admission_bot_persistence")

    logging.info("Starting parser to fetch curricula...")
    parser = ItmoParser()
    curricula = parser.get_all_programs()
    recommender = RecommendationService(curricula)
    logging.info("Curricula loaded and recommender is ready.")

    bot = AdmissionBot(curricula=curricula, recommender=recommender)

    application = Application.builder().token(token).persistence(persistence).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", bot.start)],
        states={
            PROGRAM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.program_selected)
            ],
            BACKGROUND: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.background_received)
            ],
            QUESTIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.answer_question)
            ],
        },
        fallbacks=[CommandHandler("cancel", bot.cancel)],
        name="admission_conversation",
        persistent=True,
    )

    application.add_handler(conv_handler)

    logging.info("Starting bot polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
