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
        # New flags for the feedback flow
        self.awaiting_feedback = False  # Flag to indicate we need to provide feedback
        self.last_evaluation = None  # Store the evaluation of last answer
        self.next_question = None  # Store the next question while waiting to present it

class IntentHandlerManager:
    """
    Manager for intent handlers that routes intents to appropriate handler functions.
    """
    def __init__(self, retrieval_system=None, question_generator=None, answer_evaluator=None, 
                 speech_recognition=None, text_to_speech=None, document_processor=None):
        """
        Initialize the intent handler manager.
        
        Args:
            retrieval_system: System for retrieving relevant document chunks
            question_generator: System for generating questions
            answer_evaluator: System for evaluating answers
            speech_recognition: Speech recognition system
            text_to_speech: Text-to-speech system
            document_processor: System for processing documents
        """
        self.session = SessionState()
        self.retrieval_system = retrieval_system
        self.question_generator = question_generator
        self.answer_evaluator = answer_evaluator
        self.speech_recognition = speech_recognition
        self.text_to_speech = text_to_speech
        self.document_processor = document_processor
        
        # Map intent types to handlers
        self.handlers = {
            "document_upload": self.handle_document_upload,
            "start_review": self.handle_start_review,
            "stop_review": self.handle_stop_review,
            "answer": self.handle_answer,
            "review_status": self.handle_review_status,
            "review_settings": self.handle_review_settings,
            "set_question_type": self.handle_set_question_type,
            "set_num_questions": self.handle_set_num_questions,
            "set_topic": self.handle_set_topic,
            "set_difficulty": self.handle_set_difficulty,
            "enable_speech": self.handle_enable_speech,
            "disable_speech": self.handle_disable_speech,
            "continue": self.handle_continue,
            "unknown": self.handle_unknown_intent
        }
    
    def handle_intent(self, intent_type: str, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route intent to appropriate handler with support for multiple intents.
        
        Args:
            intent_type: Type of intent
            intent_data: Data associated with the intent
            
        Returns:
            Response data
        """
        logger.info(f"Handling primary intent: {intent_type}")
        
        responses = []
        
        # Set processing state based on the intent type
        self._update_processing_state(intent_type)
        
        # Handle the primary intent
        handler = self.handlers.get(intent_type, self.handle_unknown_intent)
        primary_response = handler(intent_data)
        responses.append(primary_response)
        
        # Handle any additional intents
        if "additional_intents" in intent_data and intent_data["additional_intents"]:
            logger.info(f"Found {len(intent_data['additional_intents'])} additional intents")
            
            for additional_intent in intent_data["additional_intents"]:
                additional_intent_type = additional_intent["intent"]
                logger.info(f"Handling additional intent: {additional_intent_type}")
                
                add_handler = self.handlers.get(additional_intent_type, self.handle_unknown_intent)
                add_response = add_handler(additional_intent)
                responses.append(add_response)
        
        # Combine responses
        combined_response = self._combine_responses(responses)
        
        # Add speech output if enabled
        if self.session.speech_enabled and self.tts_system and "text" in combined_response:
            self.tts_system.speak(combined_response["text"])
            
        return combined_response

    def _update_processing_state(self, intent_type: str):
        """
        Update the processing state based on the intent type.
        This helps the UI show appropriate processing indicators.
        """
        if intent_type == "answer" and self.session.is_reviewing:
            # We're evaluating an answer
            import streamlit as st
            if 'processing_type' in st.session_state:
                st.session_state.processing_type = "evaluating"
        
        elif intent_type in ["start_review", "continue"] and self.session.is_reviewing:
            # We're generating a question
            import streamlit as st
            if 'processing_type' in st.session_state:
                st.session_state.processing_type = "generating"
        
        else:
            # General processing
            import streamlit as st
            if 'processing_type' in st.session_state:
                st.session_state.processing_type = "thinking"

    def _combine_responses(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine multiple intent responses into a single coherent response.
        
        Args:
            responses: List of response dictionaries
            
        Returns:
            Combined response dictionary
        """
        if not responses:
            return {"text": "I'm not sure how to respond."}
        
        if len(responses) == 1:
            return responses[0]
        
        # Start with the first response as base
        combined = responses[0].copy()
        
        # Combine text from all responses
        texts = [r["text"] for r in responses if "text" in r]
        combined["text"] = " ".join(texts)
        
        # Special case: if one response has a question, keep it
        for response in responses:
            if "question" in response:
                combined["question"] = response["question"]
                break
        
        # Special case: if one response has a session_summary, keep it
        for response in responses:
            if "session_summary" in response:
                combined["session_summary"] = response["session_summary"]
                break
        
        # Special case: if we're processing settings and then starting a review,
        # make sure the final response includes the start review details
        if any(r.get("intent") == "start_review" for r in responses):
            for response in responses:
                if response.get("intent") == "start_review" and "question" in response:
                    combined["question"] = response["question"]
                    break
        
        return combined
    
    def handle_document_upload(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document upload intent."""
        if not self.document_processor:
            return {"text": "Document processing is not available."}
            
        # Instead of claiming success, guide the user to use the upload functionality
        return {
            "text": "To upload documents, drag and drop them to the chat or click the upload button then press enter. ",
            "intent": "document_upload"
        }
    
    def handle_review_settings(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to show current review settings."""
        # Format the question type for display
        question_type_display = "Multiple Choice" if self.session.question_type == "multiple-choice" else "Free Text"
        
        # Format the difficulty for display
        difficulty_display = self.session.difficulty.capitalize()
        
        # Format topics
        topics_text = "all available topics" if not self.session.current_topics else ", ".join(self.session.current_topics)
        
        # Build the settings message
        settings_message = f"Current review settings:\n\n" + \
                          f"• Question Type: {question_type_display}\n\n" + \
                          f"• Number of Questions: {self.session.num_questions}\n\n" + \
                          f"• Difficulty: {difficulty_display}\n\n" + \
                          f"• Topics: {topics_text}\n\n" + \
                          f"• Speech Recognition: {'Enabled' if self.session.speech_enabled else 'Disabled'}"
        
        if not self.session.documents_loaded:
            settings_message += "\n\nNote: No documents have been loaded yet. Please upload a document to start a review."
            
        return {
            "text": settings_message,
            "intent": "review_settings"
        }
    
    def handle_start_review(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle start review intent."""
        if not self.session.documents_loaded:
            return {
                "text": "Please upload some documents first so I have material to review with you.",
                "intent": "start_review"
            }
            
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
                "text": f"Let's start the review session.\n\n {question_data['question']}",
                "question": question_data,
                "intent": "start_review"
            }
        else:
            return {
                "text": "Question generation is not available.",
                "intent": "start_review"
            }
    
    def handle_stop_review(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stop review intent."""
        if not self.session.is_reviewing:
            return {
                "text": "We're not currently in a review session.",
                "intent": "stop_review"
            }
            
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
            },
            "intent": "stop_review"
        }
    
    def handle_answer(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle answer intent."""
        if not self.session.is_reviewing:
            return {
                "text": "We're not currently in a review session. Would you like to start one?",
                "intent": "answer"
            }
            
        if not self.session.current_question:
            return {
                "text": "I don't have an active question for you to answer. Let me generate one.",
                "intent": "answer"
            }
            
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
            
            # Check if more questions remain in the session
            if self.session.total_answered < self.session.num_questions:
                # Generate next question but don't present it yet
                next_question = self.question_generator.generate_question(
                    topics=self.session.current_topics,
                    question_type=self.session.question_type,
                    difficulty=self.session.difficulty
                )
                # Store next question for later
                self.session.next_question = next_question
                # Set feedback flag
                self.session.awaiting_feedback = True
                self.session.last_evaluation = evaluation
                
                # Only provide feedback now, don't ask the next question yet
                return {
                    "text": f"{evaluation['feedback']} \n\nWould you like to continue to the next question?",
                    "evaluation": evaluation,
                    "intent": "answer"
                }
            else:
                # End of session
                correct = self.session.correct_answers
                total = self.session.total_answered
                accuracy = (correct / total) * 100 if total > 0 else 0
                
                # Reset the current question since we're done
                self.session.current_question = None
                self.session.is_reviewing = False
                
                return {
                    "text": f"{evaluation['feedback']} That completes our review session. You answered {correct} out of {total} questions correctly ({accuracy:.1f}%).",
                    "session_summary": {
                        "correct": correct,
                        "total": total,
                        "accuracy": accuracy
                    },
                    "intent": "answer"
                }
        else:
            return {
                "text": "Answer evaluation is not available.",
                "intent": "answer"
            }

    def handle_continue(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle continue to next question intent."""
        if not self.session.is_reviewing:
            return {
                "text": "We're not currently in a review session. Would you like to start one?",
                "intent": "continue"
            }
        
        if not self.session.awaiting_feedback:
            return {
                "text": "Please answer the current question first.",
                "intent": "continue"
            }
            
        # Reset feedback flag
        self.session.awaiting_feedback = False
        
        # Present the next question that we previously generated
        next_question = self.session.next_question
        if next_question:
            self.session.current_question = next_question
            self.session.next_question = None
            
            return {
                "text": f"Next question: {next_question['question']}",
                "question": next_question,
                "intent": "continue"
            }
        else:
            return {
                "text": "I don't have a next question prepared. Let me generate one for you.",
                "intent": "continue"
            }
    
    def handle_review_status(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle review status intent."""
        if not self.session.is_reviewing and self.session.total_answered == 0:
            return {
                "text": "You haven't started any review sessions yet.",
                "intent": "review_status"
            }
            
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
            },
            "intent": "review_status"
        }
    
    def handle_set_question_type(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set question type intent."""
        question_type = intent_data.get("question_type", "").lower()
        
        if question_type in ["multiple-choice", "multiple choice", "mc", "multiplechoice"]:
            self.session.question_type = "multiple-choice"
            return {
                "text": "I'll use multiple-choice questions for our review.",
                "intent": "set_question_type"
            }
        elif question_type in ["free-text", "free text", "open", "freetext"]:
            self.session.question_type = "free-text"
            return {
                "text": "I'll use free-text questions for our review.",
                "intent": "set_question_type"
            }
        else:
            return {
                "text": "I didn't understand that question type. I support multiple-choice or free-text questions.",
                "intent": "set_question_type"
            }
    
    def handle_set_num_questions(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set number of questions intent."""
        num_questions = intent_data.get("num_questions", 0)
        
        try:
            num_questions = int(num_questions)
            if 1 <= num_questions <= 50:
                self.session.num_questions = num_questions
                return {
                    "text": f"I'll prepare {num_questions} questions for our review session.",
                    "intent": "set_num_questions"
                }
            else:
                return {
                    "text": "Please choose a number of questions between 1 and 50.",
                    "intent": "set_num_questions"
                }
        except ValueError:
            return {
                "text": "I couldn't understand how many questions you want. Please specify a number.",
                "intent": "set_num_questions"
            }
    
    def handle_set_topic(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set topic intent with improved error handling."""
        topics = intent_data.get("topics", [])
        
        # Check if topic extraction failed
        if "topic_extraction_failed" in intent_data and intent_data["topic_extraction_failed"]:
            return {
                "text": "I couldn't clearly identify the topics you want to focus on. Please specify them using one of these formats:\n\n" +
                       "• Set topic to: machine learning, python\n" +
                       "• Change topic to neural networks\n" +
                       "• Focus on the topic of data science\n" +
                       "• Set the subject to: history and geography",
                "intent": "set_topic"
            }
        
        if not topics:
            self.session.current_topics = []
            return {
                "text": "I'll cover all available topics in the documents during our review.",
                "intent": "set_topic"
            }
            
        self.session.current_topics = topics
        topic_list = ", ".join(topics)
        return {
            "text": f"I'll focus our review on: {topic_list}.",
            "intent": "set_topic"
        }
    
    def handle_set_difficulty(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set difficulty intent."""
        difficulty = intent_data.get("difficulty", "").lower()
        
        if difficulty in ["easy", "beginner", "simple"]:
            self.session.difficulty = "easy"
            return {
                "text": "I'll set the difficulty to easy for our review.",
                "intent": "set_difficulty"
            }
        elif difficulty in ["medium", "moderate", "intermediate"]:
            self.session.difficulty = "medium"
            return {
                "text": "I'll set the difficulty to medium for our review.",
                "intent": "set_difficulty"
            }
        elif difficulty in ["hard", "difficult", "challenging", "advanced"]:
            self.session.difficulty = "hard"
            return {
                "text": "I'll set the difficulty to hard for our review.",
                "intent": "set_difficulty"
            }
        else:
            return {
                "text": "I didn't understand that difficulty level. I support easy, medium, or hard difficulty.",
                "intent": "set_difficulty"
            }
    
    def handle_enable_speech(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle enable speech intent."""
        self.session.speech_enabled = True
        return {
            "text": "Speech interaction is now enabled. I'll listen for your voice and respond with speech.",
            "intent": "enable_speech"
        }
    
    def handle_disable_speech(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle disable speech intent."""
        self.session.speech_enabled = False
        return {
            "text": "Speech interaction is now disabled. We'll continue with text only.",
            "intent": "disable_speech"
        }
    
    def handle_out_of_scope(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle intents that are outside the purpose of the study assistant.
        
        This method provides a consistent response for queries unrelated to 
        document review and study preparation.
        """
        return {
            "text": "I'm a study assistant focused on helping you review document contents. " + 
                    "I can help you with:\n\n" +
                    "• Uploading documents\n" +
                    "• Generating review questions\n" +
                    "• Testing your knowledge\n" +
                    "• Adjusting review settings\n\n" +
                    "What documents would you like to review?",
            "intent": "out_of_scope"
        }

    def handle_unknown_intent(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown intent."""
        return {
            "text": "I'm not sure what you want to do. You can upload documents, start/stop a review, " + 
                    "answer questions, check your status, or adjust the review settings.",
            "intent": "unknown"
        }