# %%
# question_generator.py
import os
import json
import openai
import random
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class QuestionGenerator:
    """
    Generates questions based on document content using LLM.
    """
    def __init__(self, retrieval_system, api_key: Optional[str] = None):
        """
        Initialize the question generator.
        
        Args:
            retrieval_system: RetrievalSystem for finding relevant document chunks
            api_key: OpenAI API key (will try to get from environment if None)
        """
        self.retrieval_system = retrieval_system
        
        # Use provided API key or get from environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key
        else:
            logger.warning("No OpenAI API key provided. Question generation will be limited.")
    
    def generate_question(self, topics: Optional[List[str]] = None, 
                          question_type: str = "multiple-choice",
                          difficulty: str = "medium") -> Dict[str, Any]:
        """
        Generate a question based on document content.
        
        Args:
            topics: Optional list of topics to focus on
            question_type: Type of question (multiple-choice or free-text)
            difficulty: Difficulty level (easy, medium, hard)
            
        Returns:
            Question data including question text, answer, and options (for MC)
        """
        # Retrieve relevant contexts for the question
        # Use a random topic from the provided list if available
        topic = random.choice(topics) if topics and len(topics) > 0 else None
        
        # Retrieve contexts for the chosen topic
        contexts = self.retrieval_system.retrieve_for_question_generation(
            topic=topic, 
            num_contexts=3
        )
        
        if not contexts:
            # Fallback for no contexts
            return self._generate_fallback_question(question_type)
        
        # Prepare context text for the LLM
        context_text = "\n\n".join([ctx['content'] for ctx in contexts])
        
        try:
            if self.api_key:
                return self._generate_with_llm(context_text, question_type, difficulty, topic)
            else:
                return self._generate_simple_question(context_text, question_type, difficulty)
        except Exception as e:
            logger.error(f"Error generating question: {str(e)}")
            return self._generate_fallback_question(question_type)
    
    def _generate_with_llm(self, context: str, question_type: str, 
                            difficulty: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """Generate a question using LLM."""
        # Create a prompt based on question type and difficulty
        if question_type == "multiple-choice":
            prompt = self._create_mc_prompt(context, difficulty, topic)
        else:
            prompt = self._create_free_text_prompt(context, difficulty, topic)
        
        # Call the OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert educational assistant creating review questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        # Parse the response
        question_text = response.choices[0].message.content.strip()
        
        try:
            # Try to parse structured JSON from response
            if "{" in question_text and "}" in question_text:
                json_str = question_text[question_text.find("{"):question_text.rfind("}")+1]
                question_data = json.loads(json_str)
                
                # Add question type to the data
                question_data["type"] = question_type
                
                return question_data
            else:
                # Manual parsing if no JSON structure found
                return self._parse_question_text(question_text, question_type)
        except json.JSONDecodeError:
            return self._parse_question_text(question_text, question_type)
    
    def _create_mc_prompt(self, context: str, difficulty: str, topic: Optional[str] = None) -> str:
        """Create a prompt for multiple-choice question generation."""
        topic_instruction = f"about {topic}" if topic else ""
        
        return f"""
        Based on the following context, create a challenging multiple-choice question {topic_instruction}.
        
        Context:
        {context}
        
        The difficulty level should be: {difficulty}
        
        Return your response as a JSON object with these fields:
        - question: The question text
        - options: Array of 4 possible answers (A, B, C, D)
        - answer: The correct option letter (A, B, C, or D)
        - explanation: Brief explanation of why the answer is correct
        
        Make sure the options are clearly distinct and that only one answer is truly correct.
        """
    
    def _create_free_text_prompt(self, context: str, difficulty: str, topic: Optional[str] = None) -> str:
        """Create a prompt for free-text question generation."""
        topic_instruction = f"about {topic}" if topic else ""
        
        return f"""
        Based on the following context, create a thoughtful free-text question {topic_instruction} that requires understanding and analysis.
        
        Context:
        {context}
        
        The difficulty level should be: {difficulty}
        
        Return your response as a JSON object with these fields:
        - question: The question text
        - answer: A model answer to the question
        - key_points: 3-5 key points that should be present in a good answer
        
        The question should be specific enough that it can be answered based on the context, but open-ended enough to allow for some analysis.
        """
    
    def _parse_question_text(self, text: str, question_type: str) -> Dict[str, Any]:
        """Manually parse question text if JSON parsing fails."""
        lines = text.split('\n')
        question = ""
        options = []
        answer = ""
        explanation = ""
        key_points = []
        
        # Basic parsing for multiple-choice
        if question_type == "multiple-choice":
            # First line is usually the question
            question = lines[0].strip()
            
            # Look for options (A, B, C, D)
            for line in lines[1:]:
                if line.strip().startswith(('A)', 'B)', 'C)', 'D)', 'A.', 'B.', 'C.', 'D.')):
                    option = line.strip()[2:].strip()
                    options.append(option)
                elif "answer" in line.lower() or "correct" in line.lower():
                    # Try to extract the answer letter
                    if "A" in line and "A)" in text:
                        answer = "A"
                    elif "B" in line and "B)" in text:
                        answer = "B"
                    elif "C" in line and "C)" in text:
                        answer = "C"
                    elif "D" in line and "D)" in text:
                        answer = "D"
                elif "explanation" in line.lower():
                    explanation = line.replace("Explanation:", "").strip()
        else:
            # Free-text parsing
            question = lines[0].strip()
            
            # Find answer paragraph
            answer_idx = -1
            for i, line in enumerate(lines):
                if "answer" in line.lower() or "response" in line.lower():
                    answer_idx = i
                    break
            
            if answer_idx > 0 and answer_idx < len(lines) - 1:
                answer = lines[answer_idx + 1].strip()
            
            # Try to find key points
            for line in lines:
                if "key point" in line.lower() or "important" in line.lower():
                    key_point = line.strip()
                    if ":" in key_point:
                        key_point = key_point.split(":", 1)[1].strip()
                    key_points.append(key_point)
        
        # Create question data
        question_data = {
            "type": question_type,
            "question": question
        }
        
        if question_type == "multiple-choice":
            question_data["options"] = options[:4]  # Limit to 4 options
            question_data["answer"] = answer
            question_data["explanation"] = explanation
        else:
            question_data["answer"] = answer
            question_data["key_points"] = key_points
        
        return question_data
    
    def _generate_simple_question(self, context: str, question_type: str, difficulty: str) -> Dict[str, Any]:
        """Generate a simple question when no LLM is available."""
        # Extract sentences from context
        sentences = [s.strip() for s in context.split('.') if len(s.strip()) > 20]
        
        if not sentences:
            return self._generate_fallback_question(question_type)
        
        # Select a random sentence for the question
        question_sentence = random.choice(sentences)
        
        # Create a simple question by asking about the sentence
        if question_type == "multiple-choice":
            # Create a cloze question
            words = question_sentence.split()
            if len(words) < 5:
                return self._generate_fallback_question(question_type)
            
            # Select a word to remove (not from the beginning or end)
            idx = random.randint(2, len(words) - 2)
            answer_word = words[idx]
            words[idx] = "______"
            
            question = " ".join(words)
            
            # Create distractors (other random words from the context)
            all_words = context.split()
            all_words = [w for w in all_words if len(w) > 3 and w != answer_word]
            distractors = random.sample(all_words, min(3, len(all_words)))
            
            # Ensure we have enough options
            while len(distractors) < 3:
                distractors.append("None of the above")
            
            # Create options and shuffle
            options = [answer_word] + distractors
            random.shuffle(options)
            
            # Find the correct answer letter
            answer_idx = options.index(answer_word)
            answer_letter = chr(65 + answer_idx)  # Convert to A, B, C, D
            
            return {
                "type": "multiple-choice",
                "question": f"Complete the following sentence: {question}",
                "options": options,
                "answer": answer_letter,
                "explanation": f"The correct word is '{answer_word}' based on the context."
            }
        else:
            # Free-text question
            return {
                "type": "free-text",
                "question": f"Explain the following concept in your own words: {question_sentence}",
                "answer": question_sentence,
                "key_points": [s.strip() for s in sentences[:3] if s != question_sentence]
            }
    
    def _generate_fallback_question(self, question_type: str) -> Dict[str, Any]:
        """Generate a fallback question when no context is available."""
        if question_type == "multiple-choice":
            return {
                "type": "multiple-choice",
                "question": "What is the primary purpose of a retrieval system in a conversational AI?",
                "options": [
                    "To generate random responses",
                    "To find relevant information from a knowledge base",
                    "To create visual charts and graphs",
                    "To translate text between languages"
                ],
                "answer": "B",
                "explanation": "The primary purpose of a retrieval system is to find and retrieve relevant information from a knowledge base or document store to help answer questions accurately."
            }
        else:
            return {
                "type": "free-text",
                "question": "Explain how a retrieval-augmented generation (RAG) system works and why it's useful for conversational AI?",
                "answer": "A retrieval-augmented generation system combines information retrieval with text generation. It first finds relevant documents or passages from a knowledge base, then uses those as context for generating accurate and informative responses.",
                "key_points": [
                    "Combines retrieval and generation",
                    "Uses vector search to find relevant information",
                    "Provides context to the language model",
                    "Improves accuracy of responses",
                    "Reduces hallucination in AI responses"
                ]
            }

# %%
# Mock a retrieval system for testing 
class MockRetrievalSystem:
    def retrieve_for_question_generation(self, topic=None, num_contexts=3):
        # Return some mock contexts for the topic
        return [
            {"content": "This is a sample document about machine learning."},
            {"content": "Machine learning is a subfield of artificial intelligence."},
            {"content": "A common technique in machine learning is supervised learning."}
        ]


# Initialize the QuestionGenerator with the mock retrieval system
mock_retrieval_system = MockRetrievalSystem()
question_generator = QuestionGenerator(retrieval_system=mock_retrieval_system)

# Test the question generation
topics = ["machine learning", "artificial intelligence", "data science"]  # Example topics
question_data = question_generator.generate_question(topics=topics, question_type="multiple-choice", difficulty="medium")

# Display the generated question
print("Generated Question:", question_data.get("question"))
print("Options:", question_data.get("options"))
print("Answer:", question_data.get("answer"))
print("Explanation:", question_data.get("explanation"))



