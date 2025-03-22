# intent_handlers.py
from typing import Dict, Any, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)

class SessionState:
    """Class to maintain conversation state throughout the session."""
    def __init__(self):
        self.question_type = "multiple-choice"  # or "free-text"
        self.num_questions = 5
        self.current_topics = []
        self.difficulty = "medium"  # "easy", "medium", "hard"
        self.current_question = None
        self.question_history = []
        self.correct_answers = 0
        self.total_answered = 0
        self.is_reviewing = False
        self.documents_loaded = False
        self.speech_enabled = False

class IntentHandlerManager:
    """
    Manager for intent handlers that routes intents to appropriate handler functions.
    """
    def __init__(self, retrieval_system=None, question_generator=None, answer_evaluator=None, 
                 speech_recognition=None, tts_system=None, document_processor=None):
        """
        Initialize the intent handler manager.
        
        Args:
            retrieval_system: System for retrieving relevant document chunks
            question_generator: System for generating questions
            answer_evaluator: System for evaluating answers
            speech_recognition: Speech recognition system
            tts_system: Text-to-speech system
            document_processor: System for processing documents
        """
        self.session = SessionState()
        self.retrieval_system = retrieval_system
        self.question_generator = question_generator
        self.answer_evaluator = answer_evaluator
        self.speech_recognition = speech_recognition
        self.tts_system = tts_system
        self.document_processor = document_processor
        
        # Map intent types to handlers
        self.handlers = {
            "document_upload": self.handle_document_upload,
            "start_review": self.handle_start_review,
            "stop_review": self.handle_stop_review,
            "answer": self.handle_answer,
            "review_status": self.handle_review_status,
            "set_question_type": self.handle_set_question_type,
            "set_num_questions": self.handle_set_num_questions,
            "set_topic": self.handle_set_topic,
            "set_difficulty": self.handle_set_difficulty,
            "enable_speech": self.handle_enable_speech,
            "disable_speech": self.handle_disable_speech,
            "unknown": self.handle_unknown_intent
        }
    
    def handle_intent(self, intent_type: str, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route intent to appropriate handler.
        
        Args:
            intent_type: Type of intent
            intent_data: Data associated with the intent
            
        Returns:
            Response data
        """
        logger.info(f"Handling intent: {intent_type}")
        
        handler = self.handlers.get(intent_type, self.handle_unknown_intent)
        response = handler(intent_data)
        
        # Add speech output if enabled
        if self.session.speech_enabled and self.tts_system and "text" in response:
            self.tts_system.speak(response["text"])
            
        return response
    
    def handle_document_upload(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document upload intent."""
        if not self.document_processor:
            return {"text": "Document processing is not available."}
            
        try:
            # Process the document - this would be handled by Person A's code
            document_data = intent_data.get("document_data")
            success = True  # Placeholder for actual processing
            
            if success:
                self.session.documents_loaded = True
                return {"text": "Document uploaded and processed successfully. I can now review that content with you."}
            else:
                return {"text": "There was an issue processing your document. Please try again."}
        except Exception as e:
            logger.error(f"Error in document upload: {str(e)}")
            return {"text": "An error occurred while processing your document."}
    
    def handle_start_review(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle start review intent."""
        if not self.session.documents_loaded:
            return {"text": "Please upload some documents first so I have material to review with you."}
            
        self.session.is_reviewing = True
        
        # Generate the first question
        if self.question_generator:
            question_data = self.question_generator.generate_question(
                topics=self.session.current_topics,
                question_type=self.session.question_type,
                difficulty=self.session.difficulty
            )
            
            self.session.current_question = question_data
            
            return {
                "text": f"Let's start the review session. {question_data['question']}",
                "question": question_data
            }
        else:
            return {"text": "Question generation is not available."}
    
    def handle_stop_review(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stop review intent."""
        if not self.session.is_reviewing:
            return {"text": "We're not currently in a review session."}
            
        self.session.is_reviewing = False
        
        # Generate summary of the session
        correct = self.session.correct_answers
        total = self.session.total_answered
        accuracy = (correct / total) * 100 if total > 0 else 0
        
        return {
            "text": f"Review session ended. You answered {correct} out of {total} questions correctly ({accuracy:.1f}%).",
            "session_summary": {
                "correct": correct,
                "total": total,
                "accuracy": accuracy
            }
        }
    
    def handle_answer(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle answer intent."""
        if not self.session.is_reviewing:
            return {"text": "We're not currently in a review session. Would you like to start one?"}
            
        if not self.session.current_question:
            return {"text": "I don't have an active question for you to answer. Let me generate one."}
            
        user_answer = intent_data.get("answer", "")
        
        if self.answer_evaluator:
            evaluation = self.answer_evaluator.evaluate_answer(
                question=self.session.current_question,
                user_answer=user_answer
            )
            
            # Update session stats
            self.session.total_answered += 1
            if evaluation["is_correct"]:
                self.session.correct_answers += 1
                
            # Save question and answer to history
            self.session.question_history.append({
                "question": self.session.current_question,
                "user_answer": user_answer,
                "evaluation": evaluation
            })
            
            # Generate next question if needed
            next_question = None
            if self.session.total_answered < self.session.num_questions:
                next_question = self.question_generator.generate_question(
                    topics=self.session.current_topics,
                    question_type=self.session.question_type,
                    difficulty=self.session.difficulty
                )
                self.session.current_question = next_question
                
            response = {
                "text": f"{evaluation['feedback']}",
                "evaluation": evaluation
            }
            
            if next_question:
                response["text"] += f" Next question: {next_question['question']}"
                response["question"] = next_question
            else:
                # End of session
                correct = self.session.correct_answers
                total = self.session.total_answered
                accuracy = (correct / total) * 100 if total > 0 else 0
                
                response["text"] += f" That completes our review session. You answered {correct} out of {total} questions correctly ({accuracy:.1f}%)."
                response["session_summary"] = {
                    "correct": correct,
                    "total": total,
                    "accuracy": accuracy
                }
                self.session.is_reviewing = False
                
            return response
        else:
            return {"text": "Answer evaluation is not available."}
    
    def handle_review_status(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle review status intent."""
        if not self.session.is_reviewing and self.session.total_answered == 0:
            return {"text": "You haven't started any review sessions yet."}
            
        correct = self.session.correct_answers
        total = self.session.total_answered
        remaining = self.session.num_questions - total if self.session.is_reviewing else 0
        accuracy = (correct / total) * 100 if total > 0 else 0
        
        status_text = f"You've answered {correct} out of {total} questions correctly ({accuracy:.1f}%)."
        if self.session.is_reviewing:
            status_text += f" There are {remaining} questions remaining in this session."
            
        return {
            "text": status_text,
            "session_status": {
                "correct": correct,
                "total": total,
                "remaining": remaining,
                "accuracy": accuracy,
                "is_reviewing": self.session.is_reviewing
            }
        }
    
    def handle_set_question_type(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set question type intent."""
        question_type = intent_data.get("question_type", "").lower()
        
        if question_type in ["multiple-choice", "multiple choice", "mc", "multiplechoice"]:
            self.session.question_type = "multiple-choice"
            return {"text": "I'll use multiple-choice questions for our review."}
        elif question_type in ["free-text", "free text", "open", "freetext"]:
            self.session.question_type = "free-text"
            return {"text": "I'll use free-text questions for our review."}
        else:
            return {"text": "I didn't understand that question type. I support multiple-choice or free-text questions."}
    
    def handle_set_num_questions(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set number of questions intent."""
        num_questions = intent_data.get("num_questions", 0)
        
        try:
            num_questions = int(num_questions)
            if 1 <= num_questions <= 50:
                self.session.num_questions = num_questions
                return {"text": f"I'll prepare {num_questions} questions for our review session."}
            else:
                return {"text": "Please choose a number of questions between 1 and 50."}
        except ValueError:
            return {"text": "I couldn't understand how many questions you want. Please specify a number."}
    
    def handle_set_topic(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set topic intent."""
        topics = intent_data.get("topics", [])
        
        if not topics:
            self.session.current_topics = []
            return {"text": "I'll cover all available topics in the documents during our review."}
            
        self.session.current_topics = topics
        topic_list = ", ".join(topics)
        return {"text": f"I'll focus our review on: {topic_list}."}
    
    def handle_set_difficulty(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set difficulty intent."""
        difficulty = intent_data.get("difficulty", "").lower()
        
        if difficulty in ["easy", "beginner", "simple"]:
            self.session.difficulty = "easy"
            return {"text": "I'll set the difficulty to easy for our review."}
        elif difficulty in ["medium", "moderate", "intermediate"]:
            self.session.difficulty = "medium"
            return {"text": "I'll set the difficulty to medium for our review."}
        elif difficulty in ["hard", "difficult", "challenging", "advanced"]:
            self.session.difficulty = "hard"
            return {"text": "I'll set the difficulty to hard for our review."}
        else:
            return {"text": "I didn't understand that difficulty level. I support easy, medium, or hard difficulty."}
    
    def handle_enable_speech(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle enable speech intent."""
        self.session.speech_enabled = True
        return {"text": "Speech interaction is now enabled. I'll listen for your voice and respond with speech."}
    
    def handle_disable_speech(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle disable speech intent."""
        self.session.speech_enabled = False
        return {"text": "Speech interaction is now disabled. We'll continue with text only."}
    
    def handle_unknown_intent(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown intent."""
        return {
            "text": "I'm not sure what you want to do. You can upload documents, start/stop a review, " + 
                    "answer questions, check your status, or adjust the review settings."
        }