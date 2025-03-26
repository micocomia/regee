# answer_evaluator.py
import os
import json
import logging
import requests
import traceback
from typing import Dict, Any, List, Optional, Union, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer, util

logger = logging.getLogger(__name__)


class AnswerEvaluator:
    """
    Evaluates user answers to questions using various LLM options.
    Supports multiple backend options for text evaluation including local TinyLLama LLM and Ollama.
    """

    def __init__(self,
                 llm_backend: str = "similarity",
                 use_ollama: bool = True):
        """
        Initialize the answer evaluator.

        Args:
            llm_backend: LLM backend to use ('local', 'ollama', or 'similarity')
            use_ollama: Whether to try using Ollama LLMs
        """
        self.llm_backend = llm_backend.lower()
        self.use_ollama = use_ollama

        # Initialize Ollama capability if requested
        self.ollama_available = False
        if self.use_ollama:
            self._setup_ollama_llm()

            # Set up Ollama if explicitly requested as backend
            if self.llm_backend == "ollama" and not self.ollama_available:
                logger.warning("Ollama backend requested but not available. Falling back to similarity.")
                self.llm_backend = "similarity"

        # Always set up the similarity model as a fallback
        self.similarity_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info(f"Using {self.llm_backend} backend for answer evaluation")

    def _setup_ollama_llm(self):
        """Setup the Ollama LLM integration."""
        try:
            self.ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")
            self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

            # Test connection to Ollama
            response = requests.get(self.ollama_endpoint.replace("/generate", "/tags"))
            if response.status_code == 200:
                self.ollama_available = True
                available_models = response.json().get("models", [])
                model_names = [model.get("name") for model in available_models]

                # If our preferred model isn't available, choose one that is
                if self.ollama_model not in model_names and model_names:
                    self.ollama_model = model_names[0]
                    logger.info(f"Selected available Ollama model: {self.ollama_model}")

                logger.info(f"Ollama integration available with model: {self.ollama_model}")
            else:
                self.ollama_available = False
                logger.warning("Ollama server responded but with an error")
        except Exception as e:
            self.ollama_available = False
            logger.warning(f"Ollama integration not available: {e}")

    def evaluate_answer(self, question: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """
        Evaluate a user's answer to a question.

        Args:
            question: Question data including the correct answer
            user_answer: User's answer to evaluate

        Returns:
            Evaluation results including correctness and feedback
        """
        # For multiple-choice questions, do a simple comparison
        if question.get("type") == "multiple-choice":
            return self._evaluate_multiple_choice(question, user_answer)
        else:
            # For free-text questions, use the selected backend
            try:
                # Determine which LLM to use based on backend selection and availability
                if self.llm_backend == "ollama" and self.ollama_available:
                    return self._evaluate_with_ollama(question, user_answer)
                else:
                    if self.ollama_available and self.use_ollama:
                        try:
                            return self._evaluate_with_ollama(question, user_answer)
                        except Exception as e:
                            logger.warning(f"Ollama evaluation failed: {e}")

                    # Fallback to semantic similarity if nothing else works
                    return self._evaluate_with_similarity(question, user_answer)
            except Exception as e:
                logger.error(f"Error in answer evaluation: {str(e)}")
                return self._evaluate_with_similarity(question, user_answer)

    def _evaluate_multiple_choice(self, question: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """Evaluate multiple-choice answer."""
        correct_answer = question.get("answer", "")
        options = question.get("options", [])

        # Clean up user answer to handle different formats
        user_answer = user_answer.strip().lower()

        # Handle if user provided the answer text instead of option letter
        if len(user_answer) > 1:
            # User may have typed out the full answer
            for i, option in enumerate(options):
                if  user_answer in option.lower():
                    user_answer = chr(65 + i)  # Convert to A, B, C, etc.
                    break

        is_correct = user_answer.upper() == correct_answer.upper()

        # Create feedback
        if is_correct:
            feedback = f"Correct! {options[ord(correct_answer.upper()) - 65]} is the right answer."
        else:
            correct_option = options[ord(correct_answer.upper()) - 65]
            feedback = f"That's not quite right. The correct answer is {correct_answer}.\n\nExplanation: {correct_option}"

            # Add explanation if available
            if "explanation" in question:
                feedback += f" {question['explanation']}"

        return {
            "is_correct": is_correct,
            "feedback": feedback,
            "user_answer": user_answer,
            "correct_answer": correct_answer
        }

    def _evaluate_with_ollama(self, question: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """Evaluate free-text answer using Ollama."""
        try:
            reference_answer = question.get("answer", "")
            key_points = question.get("key_points", [])

            # Create a prompt for the model
            prompt = f"""
            You are an expert educational evaluator. Assess this student answer with care and fairness.

            Question: {question.get('question', '')}

            Reference Answer: {reference_answer}

            Key Points That Should Be Included:
            {' '.join([f'- {point}' for point in key_points])}

            Student's Answer: {user_answer}

            Evaluate the student's answer based on the reference answer and key points. Provide:
            1. Is the answer correct (Yes/No/Partially)?
            2. Feedback explaining the evaluation. Address the student directly in your feedback.

            IMPORTANT REQUIREMENTS:
            1. Do NOT add ANY introductory text.
            2. The output must be in valid JSON format only.
            3. Start your response with the opening curly brace '{{' and end with a closing curly brace '}}'.
            4. Do not add any explanatory text before or after the JSON.
            5. Ensure that the feedback is informative but concise.
            
            JSON OUTPUT REQUIREMENTS:
            {{
                "is_correct": true/false,
                "feedback": "Your feedback here"
            }}
            """

            # Prepare the request to Ollama
            data = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent evaluations
                    "top_p": 0.9,
                    "top_k": 40,
                    "num_predict": 1024
                }
            }

            # Call the Ollama API
            response = requests.post(self.ollama_endpoint, json=data)

            if response.status_code == 200:
                result = response.json()
                evaluation_text = result.get("response", "")

                # Try to parse structured JSON from response
                if "{" in evaluation_text and "}" in evaluation_text:
                    json_str = evaluation_text[evaluation_text.find("{"):evaluation_text.rfind("}") + 1]
                    try:
                        evaluation = json.loads(json_str)

                        # Ensure required fields
                        if "is_correct" not in evaluation:
                            evaluation[
                                "is_correct"] = "yes" in evaluation_text.lower() or "correct" in evaluation_text.lower()
                        if "feedback" not in evaluation:
                            evaluation["feedback"] = evaluation_text

                        return evaluation
                    except json.JSONDecodeError:
                        # Handle JSON parsing errors
                        pass

                # Simple parsing if JSON parsing failed
                is_correct = "yes" in evaluation_text.lower() or "correct" in evaluation_text.lower()
                is_partially_correct = "partially" in evaluation_text.lower() or "not entirely" in evaluation_text.lower()

                if is_partially_correct:
                    is_correct = False  # If partially correct, it's not fully correct

                return {
                    "is_correct": is_correct,
                    "is_partially_correct": is_partially_correct,
                    "feedback": evaluation_text,
                    "user_answer": user_answer,
                    "reference_answer": reference_answer
                }
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return self._evaluate_with_similarity(question, user_answer)

        except Exception as e:
            logger.error(f"Error in Ollama evaluation: {str(e)}")
            return self._evaluate_with_similarity(question, user_answer)

    def _evaluate_with_similarity(self, question: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """Evaluate free-text answer using semantic similarity."""
        reference_answer = question.get("answer", "")
        key_points = question.get("key_points", [])

        try:
            # Get embeddings for both answers
            reference_embedding = self.similarity_model.encode(reference_answer, convert_to_tensor=True)
            user_embedding = self.similarity_model.encode(user_answer, convert_to_tensor=True)

            # Calculate cosine similarity
            cosine_score = util.pytorch_cos_sim(reference_embedding, user_embedding).item()

            # Check for key points coverage if available
            key_points_coverage = 0
            if key_points:
                key_point_scores = []
                for point in key_points:
                    point_embedding = self.similarity_model.encode(point, convert_to_tensor=True)
                    point_score = util.pytorch_cos_sim(point_embedding, user_embedding).item()
                    key_point_scores.append(point_score)

                # Calculate what percentage of key points are covered (similarity > 0.6)
                covered_points = sum(1 for score in key_point_scores if score > 0.6)
                key_points_coverage = covered_points / len(key_points)

            # Determine correctness based on similarity threshold and key points
            is_correct = cosine_score >= 0.75 or key_points_coverage >= 0.8
            is_partially_correct = (0.5 <= cosine_score < 0.75) or (0.4 <= key_points_coverage < 0.8)

            # Generate feedback based on similarity
            if is_correct:
                feedback = "Correct! Your answer covers the key points in the reference answer."
            elif is_partially_correct:
                feedback = "Partially correct. Your answer has some similarities with the reference answer, but is missing some key points."

                # Add missing key points if available
                if key_points:
                    missing_points = []
                    for i, point in enumerate(key_points):
                        if key_point_scores[i] < 0.6:  # This point wasn't well covered
                            missing_points.append(point)

                    if missing_points:
                        feedback += "\n\nYour answer could be improved by including these points:"
                        for point in missing_points:
                            feedback += f"\n- {point}"

                # Add the reference answer for comparison
                feedback += f"\n\nA more complete answer would be: {reference_answer}"
            else:
                feedback = f"Your answer differs significantly from the reference answer. A better answer would be: {reference_answer}"

            return {
                "is_correct": is_correct,
                "is_partially_correct": is_partially_correct,
                "feedback": feedback,
                "user_answer": user_answer,
                "reference_answer": reference_answer,
                "similarity_score": cosine_score,
                "key_points_coverage": key_points_coverage if key_points else None
            }
        except Exception as e:
            logger.error(f"Error in similarity evaluation: {str(e)}")
            return self._simple_keyword_evaluation(question, user_answer)

    def _simple_keyword_evaluation(self, question: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """Simple keyword-based evaluation as ultimate fallback."""
        reference_answer = question.get("answer", "")
        key_points = question.get("key_points", [])

        # Convert to lowercase for comparison
        user_lower = user_answer.lower()
        reference_lower = reference_answer.lower()

        # Check for key points coverage
        key_points_covered = 0
        if key_points:
            for point in key_points:
                # Check if keywords from the point are in the answer
                keywords = [w for w in point.lower().split() if len(w) > 3]  # Only meaningful words
                matches = sum(1 for k in keywords if k in user_lower)
                if matches >= len(keywords) * 0.5:  # If at least half the keywords match
                    key_points_covered += 1

            key_points_coverage = key_points_covered / len(key_points)
        else:
            # Get keywords from reference answer if no key points
            keywords = reference_lower.split()
            keywords = [k for k in keywords if len(k) > 3]  # Only keep meaningful words

            # Count matching keywords
            matches = sum(1 for k in keywords if k in user_lower)
            key_points_coverage = matches / len(keywords) if keywords else 0

        # Determine correctness based on keyword match ratio
        is_correct = key_points_coverage >= 0.7  # Threshold for correctness
        is_partially_correct = 0.3 <= key_points_coverage < 0.7

        # Generate feedback
        if is_correct:
            feedback = "Correct! Your answer contains the key concepts."
        elif is_partially_correct:
            feedback = "Partially correct. Your answer addresses some key points but could be more complete."

            # Add missing key points if available
            if key_points:
                feedback += "\n\nConsider including these points in your answer:"
                for point in key_points:
                    keywords = [w for w in point.lower().split() if len(w) > 3]
                    matches = sum(1 for k in keywords if k in user_lower)
                    if matches < len(keywords) * 0.5:  # This point wasn't covered well
                        feedback += f"\n- {point}"
        else:
            feedback = f"Your answer is missing important concepts. A better answer would be: {reference_answer}"

        return {
            "is_correct": is_correct,
            "is_partially_correct": is_partially_correct,
            "feedback": feedback,
            "user_answer": user_answer,
            "reference_answer": reference_answer,
            "key_points_coverage": key_points_coverage
        }

    def debug_answer_evaluation(self, question: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """
        Debug version of evaluate_answer with detailed logging.

        Args:
            question: Question data including the correct answer
            user_answer: User's answer to evaluate

        Returns:
            Evaluation results and debug information
        """
        print("\n=== STARTING ANSWER EVALUATION DEBUGGING ===")
        print(f"Question type: {question.get('type', 'unknown')}")
        print(f"Question: {question.get('question', '')}")
        print(f"Reference answer: {question.get('answer', '')[:100]}...")
        print(f"User answer: {user_answer[:100]}...")

        debug_info = {
            "question_type": question.get("type", "unknown"),
            "evaluation_attempts": [],
            "final_evaluation": None
        }

        # For multiple-choice, use the direct evaluation
        if question.get("type") == "multiple-choice":
            print("\nPerforming multiple-choice evaluation.")
            result = self._evaluate_multiple_choice(question, user_answer)
            print(f"Evaluation result: {'Correct' if result.get('is_correct') else 'Incorrect'}")
            debug_info["final_evaluation"] = result
            print("\n=== ANSWER EVALUATION DEBUGGING COMPLETE ===")
            return debug_info

        # For free-text, try different evaluation methods
        # Try Ollama if available
        if self.ollama_available and self.use_ollama:
            print("\n=== Attempting Ollama evaluation ===")
            try:
                ollama_result = self._evaluate_with_ollama(question, user_answer)
                print(f"Ollama evaluation result: {'Correct' if ollama_result.get('is_correct') else 'Incorrect'}")
                print(f"Feedback sample: {ollama_result.get('feedback', '')[:100]}...")
                debug_info["evaluation_attempts"].append({
                    "method": "ollama",
                    "result": ollama_result,
                    "success": True
                })

                # If we're using Ollama as the primary backend, use this result
                if self.llm_backend == "ollama":
                    debug_info["final_evaluation"] = ollama_result
                    print("\n=== ANSWER EVALUATION DEBUGGING COMPLETE ===")
                    return debug_info
            except Exception as e:
                print(f"Ollama evaluation failed: {str(e)}")
                traceback.print_exc()
                debug_info["evaluation_attempts"].append({
                    "method": "ollama",
                    "error": str(e),
                    "success": False
                })
        else:
            print("\nSkipping Ollama (not available or disabled)")

        # Fall back to similarity-based evaluation
        print("\n=== Falling back to similarity-based evaluation ===")
        try:
            similarity_result = self._evaluate_with_similarity(question, user_answer)
            print(f"Similarity evaluation result: {'Correct' if similarity_result.get('is_correct') else 'Incorrect'}")
            print(f"Similarity score: {similarity_result.get('similarity_score', 0)}")
            print(f"Key points coverage: {similarity_result.get('key_points_coverage')}")
            print(f"Feedback sample: {similarity_result.get('feedback', '')[:100]}...")
            debug_info["evaluation_attempts"].append({
                "method": "similarity",
                "result": similarity_result,
                "success": True
            })

            debug_info["final_evaluation"] = similarity_result
        except Exception as e:
            print(f"Similarity evaluation failed: {str(e)}")
            traceback.print_exc()
            debug_info["evaluation_attempts"].append({
                "method": "similarity",
                "error": str(e),
                "success": False
            })

            # Final fallback to keyword evaluation
            print("\n=== Final fallback to keyword evaluation ===")
            keyword_result = self._simple_keyword_evaluation(question, user_answer)
            print(f"Keyword evaluation result: {'Correct' if keyword_result.get('is_correct') else 'Incorrect'}")
            print(f"Key points coverage: {keyword_result.get('key_points_coverage')}")
            debug_info["evaluation_attempts"].append({
                "method": "keyword",
                "result": keyword_result,
                "success": True
            })

            debug_info["final_evaluation"] = keyword_result

        print("\n=== ANSWER EVALUATION DEBUGGING COMPLETE ===")
        return debug_info