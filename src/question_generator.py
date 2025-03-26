# question_generator.py
import os
import json
import random
import requests
import traceback  # Add this at the top
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class QuestionGenerator:
    """
    Generates high-quality educational questions based on document content using local LLMs.
    """
    def __init__(self, retrieval_system, use_ollama: bool = True):
        """
        Initialize the question generator.
        
        Args:
            retrieval_system: RetrievalSystem for finding relevant document chunks
            use_ollama: Whether to try using Ollama LLMs
        """
        self.retrieval_system = retrieval_system
        self.use_ollama = use_ollama
        
        # Initialize Ollama capability if requested
        self.ollama_available = False
        if self.use_ollama:
            self._setup_ollama_llm()
    
    def generate_question(self, topics: Optional[List[str]] = None, 
                         question_type: str = "multiple-choice",
                         difficulty: str = "medium") -> Dict[str, Any]:
        """
        Generate a question based on document content with validation.
        
        Args:
            topics: Optional list of topics to focus on
            question_type: Type of question (multiple-choice or free-text)
            difficulty: Difficulty level (easy, medium, hard)
            
        Returns:
            Question data including question text, answer, and options (for MC)
        """
        # Maximum attempts to generate a valid question
        max_attempts = 3
        
        for attempt in range(max_attempts):
            # Retrieve relevant contexts for the question
            topic = random.choice(topics) if topics and len(topics) > 0 else None
            
            # Use the improved context retrieval
            contexts = self.retrieval_system.retrieve_for_question_generation(
                topic=topic, 
                num_contexts=100
            )
            
            if not contexts:
                # Fallback for no contexts
                return self._generate_fallback_question(question_type)
            
            # Prepare context text for the LLM
            context_text = "\n\n".join([ctx['content'] for ctx in contexts])
            
            try:
                # Determine which LLM to use based on availability
                question_data = None
                
                # Try Ollama if available
                if question_data is None and self.ollama_available and self.use_ollama:
                    try:
                        logger.info(f"Attempting to generate question with Ollama")
                        question_data = self._generate_with_ollama(context_text, question_type, difficulty, topic)
                    except Exception as e:
                        logger.warning(f"Ollama generation failed: {e}")
                        question_data = None
                
                # Use simple generation as final fallback
                if question_data is None:
                    logger.info(f"Using simple question generation as fallback")
                    question_data = self._generate_simple_question(context_text, question_type, difficulty)
                
                # Validate the question
                is_valid, reason = self._validate_question(question_data)
                
                if is_valid:
                    logger.info(f"Generated valid {question_type} question on attempt {attempt+1}")
                    # Add metadata about generation method
                    if "metadata" not in question_data:
                        question_data["metadata"] = {}
                    question_data["metadata"]["difficulty"] = difficulty
                    if topic:
                        question_data["metadata"]["topic"] = topic
                    return question_data
                else:
                    logger.warning(f"Question validation failed on attempt {attempt+1}: {reason}")
                    
                    # If last attempt, try to fix the question instead of generating a new one
                    if attempt == max_attempts - 1:
                        logger.info("Attempting to fix invalid question on final attempt")
                        question_data = self._fix_invalid_question(question_data, reason)
                        return question_data
            
            except Exception as e:
                logger.error(f"Error generating question on attempt {attempt+1}: {str(e)}")
                
                # On last attempt, return fallback
                if attempt == max_attempts - 1:
                    return self._generate_fallback_question(question_type)
        
        # Shouldn't reach here, but just in case
        return self._generate_fallback_question(question_type)
    
    def generate_knowledge_check(self, document_id: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Generate a complete knowledge check assessment from a specific document.
        
        Args:
            document_id: Identifier of the document to generate questions from
            num_questions: Number of questions to generate
            
        Returns:
            List of question data dictionaries for the knowledge check
        """
        # Get all chunks for the document
        chunks = self.retrieval_system.vector_store.collection.get(
            where={"source": document_id},
            include=["documents", "metadatas"]
        )
        
        if not chunks or not chunks["ids"]:
            logger.warning(f"No document chunks found for document ID: {document_id}")
            return []
        
        # Extract all topics from the document
        all_topics = set()
        for metadata in chunks["metadatas"]:
            if "topics" in metadata:
                topics = metadata["topics"]
                if isinstance(topics, str):
                    topic_list = [t.strip() for t in topics.split(',')]
                    all_topics.update(topic_list)
        
        # Filter out very common topics that might be too general
        filtered_topics = [t for t in all_topics if len(t) > 3]
        
        # Create a balanced set of questions
        questions = []
        
        # Map to track which topics we've used
        covered_topics = set()
        
        # Determine question distribution
        mc_count = int(num_questions * 0.7)  # 70% multiple choice
        free_text_count = num_questions - mc_count  # 30% free text
        
        # Track difficulty distribution
        difficulty_distribution = {
            "easy": int(num_questions * 0.3),
            "medium": int(num_questions * 0.5),
            "hard": num_questions - int(num_questions * 0.3) - int(num_questions * 0.5)
        }
        
        # Helper function to get next difficulty
        def get_next_difficulty():
            for diff, count in difficulty_distribution.items():
                if count > 0:
                    difficulty_distribution[diff] -= 1
                    return diff
            return "medium"  # Fallback
        
        # Generate multiple-choice questions
        for _ in range(mc_count):
            # Select a topic that hasn't been covered yet, if possible
            available_topics = [t for t in filtered_topics if t not in covered_topics]
            if not available_topics and filtered_topics:
                # If all topics covered, reset and start again
                covered_topics.clear()
                available_topics = filtered_topics
                
            topic = random.choice(available_topics) if available_topics else None
            if topic:
                covered_topics.add(topic)
                
            # Get the difficulty for this question
            difficulty = get_next_difficulty()
                
            # Generate the question
            question = self.generate_question(
                topics=[topic] if topic else None,
                question_type="multiple-choice",
                difficulty=difficulty
            )
            
            # Add additional metadata
            question["document_id"] = document_id
            question["topic"] = topic
            question["difficulty"] = difficulty
            
            questions.append(question)
        
        # Generate free-text questions
        for _ in range(free_text_count):
            # Choose from remaining topics or reset
            available_topics = [t for t in filtered_topics if t not in covered_topics]
            if not available_topics and filtered_topics:
                covered_topics.clear()
                available_topics = filtered_topics
                
            topic = random.choice(available_topics) if available_topics else None
            if topic:
                covered_topics.add(topic)
                
            # Get the difficulty for this question
            difficulty = get_next_difficulty()
            
            # Generate the question
            question = self.generate_question(
                topics=[topic] if topic else None,
                question_type="free-text",
                difficulty=difficulty
            )
            
            # Add additional metadata
            question["document_id"] = document_id
            question["topic"] = topic
            question["difficulty"] = difficulty
            
            questions.append(question)
        
        return questions
    
    def _setup_ollama_llm(self):
        """Setup the Ollama LLM integration."""
        try:
            import requests
            
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
    
    def _generate_with_ollama(self, context: str, question_type: str, 
                            difficulty: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """Generate a question using Ollama with improved JSON parsing."""
        import requests
        import json
        import re
        
        # Create a prompt based on question type and difficulty
        if question_type == "multiple-choice":
            prompt = self._create_mc_prompt(context, difficulty, topic)
        else:
            prompt = self._create_free_text_prompt(context, difficulty, topic)
        
        # Prepare the request to Ollama
        data = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 1024
            }
        }
        
        try:
            # Call the Ollama API
            response = requests.post(self.ollama_endpoint, json=data)
            
            if response.status_code == 200:
                result = response.json()
                question_text = result.get("response", "")
                
                # Log the raw response for debugging
                logger.debug(f"Raw Ollama response: {question_text[:200]}...")
                
                # Parse the response - with more robust JSON extraction
                try:
                    # First attempt: Find JSON between curly braces
                    json_match = re.search(r'\{.*\}', question_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        # Remove any markdown code block markers
                        json_str = re.sub(r'```json|```', '', json_str).strip()
                        
                        # Clean the JSON string of control characters
                        json_str = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', json_str)
                        
                        # Try to parse with error handling for each step
                        try:
                            question_data = json.loads(json_str)
                            question_data["type"] = question_type
                            return question_data
                        except json.JSONDecodeError as e:
                            logger.warning(f"JSON parsing error in first attempt: {e}")
                            
                            # Second attempt: Try to fix common JSON issues
                            try:
                                # Replace single quotes with double quotes (common LLM mistake)
                                fixed_json = re.sub(r"(?<!\\)'([^']*?)(?<!\\)'", r'"\1"', json_str)
                                # Ensure property names have double quotes
                                fixed_json = re.sub(r'(\s*)(\w+)(\s*):(\s*)', r'\1"\2"\3:\4', fixed_json)
                                question_data = json.loads(fixed_json)
                                question_data["type"] = question_type
                                return question_data
                            except json.JSONDecodeError as e2:
                                logger.warning(f"JSON parsing error in second attempt: {e2}")
                                
                                # Third attempt: Try to extract a valid JSON substring
                                try:
                                    # Find the start of a valid JSON object
                                    start_idx = json_str.find('{')
                                    # Find the corresponding closing brace
                                    open_braces = 0
                                    end_idx = -1
                                    for i in range(start_idx, len(json_str)):
                                        if json_str[i] == '{':
                                            open_braces += 1
                                        elif json_str[i] == '}':
                                            open_braces -= 1
                                        if open_braces == 0:
                                            end_idx = i + 1
                                            break
                                    
                                    if end_idx > start_idx:
                                        substring_json = json_str[start_idx:end_idx]
                                        question_data = json.loads(substring_json)
                                        question_data["type"] = question_type
                                        return question_data
                                    else:
                                        raise ValueError("Could not find matching JSON braces")
                                except (json.JSONDecodeError, ValueError) as e3:
                                    logger.warning(f"JSON parsing error in third attempt: {e3}")
                                    return self._parse_question_text(question_text, question_type)
                    else:
                        logger.warning("No JSON structure found in Ollama response")
                        return self._parse_question_text(question_text, question_type)
                except Exception as e:
                    logger.warning(f"General error in JSON parsing: {str(e)}")
                    return self._parse_question_text(question_text, question_type)
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return self._generate_simple_question(context, question_type, difficulty)
        except Exception as e:
            logger.error(f"Error with Ollama generation: {str(e)}")
            return self._generate_simple_question(context, question_type, difficulty)
        
    def _create_mc_prompt(self, context: str, difficulty: str, topic: Optional[str] = None) -> str:
        """Create a prompt for multiple-choice question generation."""
        topic_instruction = f"about {topic}" if topic else "on the key concepts in this material"
        difficulty_guidance = {
            "easy": "test basic recall and understanding of fundamental concepts",
            "medium": "require application of concepts and some analysis",
            "hard": "require deeper analysis, synthesis of multiple concepts, or evaluation"
        }.get(difficulty.lower(), "require application of concepts and some analysis")
        
        # Add specific instructions based on difficulty
        difficulty_specifics = ""
        if difficulty.lower() == "easy":
            difficulty_specifics = "Focus on testing fundamental terminology, basic principles, or straightforward facts. For example, 'What is the meaning X?' or 'How would you explain Y?'"
        elif difficulty.lower() == "medium":
            difficulty_specifics = "Focus on application of concepts, cause-and-effect relationships, or comparing and contrasting ideas. For example, 'How can you apply X to Y?' or 'What are the key arguments presented in X, and how do they relate to each other?'"
        else:  # hard
            difficulty_specifics = "Focus on analysis of complex scenarios, evaluation of approaches, predictive outcomes, or synthesizing information across multiple concepts. For example, 'What are the strengths and weaknesses of X?' or 'How would you improve Y?'"

        # Clean and sanitize the context
        # Remove any control characters and ensure JSON-safe strings
        import re
        clean_context = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', context)

        return f"""
        As an educational expert, create a high-quality multiple-choice question {topic_instruction} that would {difficulty_guidance}. If the provided context is limited or lacks detail, first supplement it with relevant information before generating questions. 
        
        Context:
        {clean_context}
        
        {difficulty_specifics}
        
        IMPORTANT REQUIREMENTS:
        1. Do NOT add ANY introductory text.
        2. The output must be in valid JSON format only.
        3. Start your response with the opening curly brace '{{' and end with a closing curly brace '}}'.
        4. Do not add any explanatory text before or after the JSON.
        5. The question should focus on substantive, meaningful content that demonstrates understanding
        6. DO NOT create questions about author names, paper titles, dates, or superficial information
        7. DO NOT create simple fill-in-the-blank questions that just remove a single word from a sentence
        8. All answer options should be plausible and of similar length and style
        9. The question should be clear, unambiguous, and test important concepts
        10. Include a concise explanation that not only explains the correct answer but also why other options are incorrect
        11. ONLY add supplementary information when NECESSARY.
        12. In the options text, DO NOT precede each option with their respective letters.
        
        JSON OUTPUT REQUIREMENTS:
        {{
            "question": "The question text here",
            "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
            "answer": "A, B, C, or D",
            "explanation": "Concise explanation of why the correct answer is right and others are wrong"
        }}
        """

    def _create_free_text_prompt(self, context: str, difficulty: str, topic: Optional[str] = None) -> str:
        """Create a prompt for free-text question generation."""
        topic_instruction = f"about {topic}" if topic else "on the key concepts in this material"
        difficulty_guidance = {
            "easy": "test basic recall and understanding",
            "medium": "require application and analysis of concepts",
            "hard": "require deep analysis, synthesis, or evaluation"
        }.get(difficulty.lower(), "require application and analysis of concepts")
        
        # Add specific question types based on difficulty
        question_types = ""
        if difficulty.lower() == "easy":
            question_types = "This could be a 'define and explain', 'identify and describe', or 'summarize' type question."
        elif difficulty.lower() == "medium":
            question_types = "This could be a 'compare and contrast', 'analyze', 'apply', or 'explain the relationship' type question."
        else:  # hard
            question_types = "This could be an 'evaluate', 'synthesize', 'propose a solution', 'predict outcomes', or 'critique' type question."
        
        # Clean and sanitize the context
        # Remove any control characters and ensure JSON-safe strings
        import re
        clean_context = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', context)
        
        return f"""As an educational expert, create a thought-provoking free-text question {topic_instruction} that would {difficulty_guidance}. If the provided context is limited or lacks detail, first supplement it with relevant information before generating questions.
    
    Context:
    {clean_context}
    
    {question_types}
    
    IMPORTANT REQUIREMENTS:
    1. Do NOT add ANY introductory text.
    2. The output must be in valid JSON format only.
    3. Start your response with the opening curly brace '{{' and end with a closing curly brace '}}'.
    4. Do not add any explanatory text before or after the JSON.
    5. Create a question that tests deeper understanding, not mere memorization
    6. The question should require original thinking, not just repeating the text
    7. DO NOT create questions about superficial details like author names or dates
    8. The question should be specific enough to be answerable from the context
    9. Include a comprehensive model answer that demonstrates what a good response would include
    10. ONLY add supplementary information when NECESSARY.
    11. Consider the difficulty of the question when providing the anser (e.g., shorter answers for easy, longer for hard)
    
    JSON OUTPUT REQUIREMENTS:
    {{
        "question": "The question text here",
        "answer": "A detailed model answer to the question",
        "key_points": ["Key point 1", "Key point 2", "Key point 3", "Key point 4"],
        "grading_criteria": ["Criterion 1", "Criterion 2", "Criterion 3", "Criterion 4"]
    }}"""
    
    def _parse_question_text(self, text: str, question_type: str) -> Dict[str, Any]:
        """Manually parse question text if JSON parsing fails."""
        lines = text.split('\n')
        question = ""
        options = []
        answer = ""
        explanation = ""
        key_points = []
        grading_criteria = []
        
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
                    # Try to get multi-line explanation
                    exp_idx = lines.index(line)
                    if exp_idx < len(lines) - 1:
                        explanation = "\n".join(lines[exp_idx+1:])
        else:
            # Free-text parsing
            question = lines[0].strip()
            
            # Find answer paragraph
            answer_idx = -1
            key_points_idx = -1
            grading_idx = -1
            
            for i, line in enumerate(lines):
                if "answer" in line.lower() or "response" in line.lower():
                    answer_idx = i
                elif "key point" in line.lower() or "key points" in line.lower():
                    key_points_idx = i
                elif "grading" in line.lower() or "criteria" in line.lower():
                    grading_idx = i
                    
            # Extract answer
            if answer_idx > 0:
                if key_points_idx > answer_idx:
                    answer = "\n".join(lines[answer_idx+1:key_points_idx]).strip()
                elif grading_idx > answer_idx:
                    answer = "\n".join(lines[answer_idx+1:grading_idx]).strip()
                else:
                    answer = "\n".join(lines[answer_idx+1:]).strip()
            
            # Extract key points
            if key_points_idx > 0:
                for i in range(key_points_idx+1, len(lines)):
                    if i == grading_idx:
                        break
                    line = lines[i].strip()
                    if line and (line.startswith('-') or line.startswith('*') or 
                              (len(line) > 2 and line[0].isdigit() and line[1] in '.) ')):
                        key_points.append(line.lstrip('-*0123456789.) '))
                
            # Extract grading criteria
            if grading_idx > 0:
                for i in range(grading_idx+1, len(lines)):
                    line = lines[i].strip()
                    if line and (line.startswith('-') or line.startswith('*') or 
                              (len(line) > 2 and line[0].isdigit() and line[1] in '.) ')):
                        grading_criteria.append(line.lstrip('-*0123456789.) '))
        
        # Create question data
        question_data = {
            "type": question_type,
            "question": question
        }
        
        if question_type == "multiple-choice":
            question_data["options"] = options[:4] if options else ["Option A", "Option B", "Option C", "Option D"]  
            question_data["answer"] = answer or "A"  # Default to A if no answer found
            question_data["explanation"] = explanation or f"The correct answer is {answer or 'A'}"
        else:
            question_data["answer"] = answer
            question_data["key_points"] = key_points if key_points else ["Key point 1", "Key point 2", "Key point 3"]
            question_data["grading_criteria"] = grading_criteria
        
        return question_data
    
    def _generate_simple_question(self, context: str, question_type: str, difficulty: str) -> Dict[str, Any]:
        """Generate a simple question when no LLM is available."""
        # Extract sentences from context
        sentences = [s.strip() for s in context.split('.') if len(s.strip()) > 20]
        
        if not sentences:
            return self._generate_fallback_question(question_type)
        
        # Select sentences with educational content for better questions
        educational_sentences = []
        for sentence in sentences:
            # Check for educational markers
            has_educational_content = any(marker in sentence.lower() for marker in 
                                         ["define", "concept", "principle", "method", 
                                         "example", "important", "note that", "key", 
                                         "understand", "approach", "theory", "technique"])
            if has_educational_content:
                educational_sentences.append(sentence)
        
        # Use educational sentences if found, otherwise use all sentences
        question_sentences = educational_sentences if educational_sentences else sentences
        
        # Select a random sentence for the question
        question_sentence = random.choice(question_sentences)
        
        # Create a question based on question type and difficulty
        if question_type == "multiple-choice":
            if difficulty.lower() == "easy":
                # Create a term definition question
                words = question_sentence.split()
                important_terms = [w for w in words if len(w) > 5 and w[0].isupper()]
                
                if important_terms:
                    term = random.choice(important_terms)
                    question = f"What is the best definition of '{term}' based on the context?"
                    
                    # Create options with the correct definition and distractors
                    term_sentence = question_sentence
                    
                    # Create distractors by modifying the correct sentence
                    distractors = []
                    for _ in range(3):
                        if random.random() < 0.5:
                            # Negate the sentence
                            if "is" in term_sentence:
                                distractor = term_sentence.replace("is", "is not")
                            elif "are" in term_sentence:
                                distractor = term_sentence.replace("are", "are not")
                            else:
                                distractor = "Not " + term_sentence
                        else:
                            # Replace key terms
                            other_sentences = [s for s in sentences if s != question_sentence]
                            if other_sentences:
                                distractor = random.choice(other_sentences)
                            else:
                                distractor = f"The opposite of what is described in the context."
                        distractors.append(distractor)
                    
                    options = [term_sentence] + distractors
                    random.shuffle(options)
                    
                    # Find the correct answer letter
                    answer_idx = options.index(term_sentence)
                    answer_letter = chr(65 + answer_idx)  # Convert to A, B, C, D
                    
                    return {
                        "type": "multiple-choice",
                        "question": question,
                        "options": options,
                        "answer": answer_letter,
                        "explanation": f"The correct definition is found directly in the context. The other options either contradict the text or present incorrect information."
                    }
            
            # Default multiple-choice approach (medium/hard or fallback)
            # Create a conceptual question rather than fill-in-the-blank
            concepts = []
            for sent in sentences:
                # Look for sentences with concept indicators
                if any(indicator in sent.lower() for indicator in ["is defined as", "refers to", "means", "is a", "are", "describes"]):
                    concepts.append(sent)
            
            if concepts:
                # Create a question about a concept
                concept_sentence = random.choice(concepts)
                # Extract the likely concept name
                concept_words = concept_sentence.split()
                # Look for capitalized terms or terms before definition indicators
                for i, word in enumerate(concept_words):
                    if word[0].isupper() and len(word) > 3:
                        concept = word
                        question = f"Which of the following best describes {concept}?"
                        break
                    elif i < len(concept_words) - 2 and concept_words[i+1].lower() in ["is", "are", "refers"]:
                        concept = word
                        question = f"Which of the following best describes {concept}?"
                        break
                else:
                    # Fallback if no concept is identified
                    question = "Which of the following statements is true according to the context?"
                    concept_sentence = question_sentence
            else:
                # Fallback if no concept sentences
                question = "Which of the following statements is true according to the context?"
                concept_sentence = question_sentence
                
            # Create distractors by modifying or contradicting the correct statement
            distractors = []
            for _ in range(3):
                other_sentences = [s for s in sentences if s != concept_sentence]
                if other_sentences:
                    distractor = random.choice(other_sentences)
                    distractors.append(distractor)
                else:
                    # Create synthetic distractors
                    if "is" in concept_sentence:
                        distractor = concept_sentence.replace("is", "is not")
                    elif "are" in concept_sentence:
                        distractor = concept_sentence.replace("are", "are not")
                    else:
                        distractor = "Not " + concept_sentence
                    distractors.append(distractor)
            
            # Ensure we have exactly 3 distractors
            while len(distractors) < 3:
                distractors.append(f"None of the above statements accurately reflect the context.")
                
            options = [concept_sentence] + distractors
            random.shuffle(options)
            
            # Find the correct answer letter
            answer_idx = options.index(concept_sentence)
            answer_letter = chr(65 + answer_idx)  # Convert to A, B, C, D
            
            return {
                "type": "multiple-choice",
                "question": question,
                "options": options,
                "answer": answer_letter,
                "explanation": f"The correct answer ({answer_letter}) is directly stated in the context. The other options either contradict this information or present unrelated content."
            }
        else:
            # Free-text question generation based on difficulty
            if difficulty.lower() == "easy":
                # "Define and explain" type question
                important_terms = []
                for sent in sentences:
                    words = sent.split()
                    for word in words:
                        if len(word) > 5 and word[0].isupper():
                            important_terms.append(word)
                
                if important_terms:
                    term = random.choice(important_terms)
                    question = f"Define and explain the concept of {term} based on the information provided in the context."
                    
                    # Find sentences containing the term for the answer
                    term_sentences = [s for s in sentences if term in s]
                    answer = ' '.join(term_sentences) if term_sentences else question_sentence
                    
                    # Key points
                    key_points = []
                    if term_sentences:
                        key_points = [f"Accurate definition of {term}", 
                                     f"Clear explanation of the significance of {term}", 
                                     "Connection to the broader context"]
                    else:
                        # Fallback key points
                        key_points = ["Accurate definition based on the context",
                                     "Clear and concise explanation",
                                     "Proper use of terminology from the source material"]
                else:
                    # Fallback if no important terms found
                    question = "Summarize the key concepts presented in this text."
                    answer = ' '.join(sentences[:3]) if len(sentences) >= 3 else context
                    key_points = ["Accurate identification of main concepts",
                                 "Concise summary covering the essential information",
                                 "Proper use of terminology from the source material"]
            
            elif difficulty.lower() == "medium":
                # "Compare and contrast" or "analyze" type question
                concepts = []
                for sent in sentences:
                    if any(indicator in sent.lower() for indicator in ["is defined as", "refers to", "means", "is a", "are", "describes"]):
                        words = sent.split()
                        for word in words:
                            if len(word) > 5 and word[0].isupper():
                                concepts.append(word)
                
                if len(concepts) >= 2:
                    # Compare and contrast question
                    concept1, concept2 = random.sample(concepts, 2)
                    question = f"Compare and contrast {concept1} and {concept2}. What are their similarities and differences based on the context?"
                    
                    # Create answer by combining relevant sentences
                    concept1_sents = [s for s in sentences if concept1 in s]
                    concept2_sents = [s for s in sentences if concept2 in s]
                    
                    answer = f"When comparing {concept1} and {concept2}, several key points emerge:\n\n"
                    answer += f"{concept1}: " + ' '.join(concept1_sents) + "\n\n"
                    answer += f"{concept2}: " + ' '.join(concept2_sents) + "\n\n"
                    answer += "The main similarities include their relevance to the subject matter, while key differences can be observed in their definitions and applications."
                    
                    key_points = [f"Clear description of {concept1}",
                                 f"Clear description of {concept2}",
                                 "Identification of meaningful similarities",
                                 "Identification of significant differences",
                                 "Use of evidence from the context to support comparisons"]
                else:
                    # Analysis question (fallback)
                    question = "Analyze the main approaches or methods described in this context. What are their key characteristics?"
                    answer = ' '.join(sentences[:4]) if len(sentences) >= 4 else context
                    key_points = ["Identification of main approaches/methods",
                                 "Analysis of key characteristics of each approach",
                                 "Evaluation of contexts where these approaches apply",
                                 "Use of evidence from the provided material"]
            
            else:  # hard
                # "Evaluate" or "synthesize" type question
                question = "Evaluate the effectiveness of the approaches described in this context. What are their strengths and limitations, and in what situations might each be most valuable?"
                
                # Create a thoughtful answer by synthesizing the content
                answer = "Based on the provided context:\n\n"
                
                # Group sentences by potential approaches
                approach_sentences = {}
                current_approach = "General"
                for sent in sentences:
                    if any(word[0].isupper() and len(word) > 5 for word in sent.split()):
                        # Potential new approach
                        for word in sent.split():
                            if word[0].isupper() and len(word) > 5:
                                current_approach = word
                                break
                    
                    if current_approach not in approach_sentences:
                        approach_sentences[current_approach] = []
                    approach_sentences[current_approach].append(sent)
                
                # Build the answer from grouped sentences
                for approach, sents in approach_sentences.items():
                    if approach != "General":
                        answer += f"{approach}:\n"
                    else:
                        answer += "General approaches:\n"
                    
                    answer += ' '.join(sents) + "\n\n"
                    
                    # Add evaluation elements
                    answer += f"Strengths: The {approach} approach provides a structured framework that can be especially valuable in complex scenarios.\n"
                    answer += f"Limitations: However, it may require more resources or specialized knowledge compared to alternatives.\n\n"
                
                answer += "In conclusion, the most effective approach depends on the specific context, available resources, and desired outcomes."
                
                key_points = ["Comprehensive evaluation of different approaches",
                             "Analysis of strengths for each approach",
                             "Critical assessment of limitations",
                             "Discussion of contextual factors affecting effectiveness",
                             "Synthesis of information to form a balanced conclusion"]
            
            return {
                "type": "free-text",
                "question": question,
                "answer": answer,
                "key_points": key_points,
                "grading_criteria": [
                    "Accuracy of information based on the provided context",
                    "Depth of analysis and critical thinking",
                    "Organization and clarity of response",
                    "Use of specific examples or evidence from the context",
                    "Proper terminology and conceptual understanding"
                ]
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
                ],
                "grading_criteria": [
                    "Accuracy of technical explanation",
                    "Understanding of both retrieval and generation components",
                    "Explanation of how RAG improves AI responses",
                    "Discussion of practical applications",
                    "Clear and organized presentation of concepts"
                ]
            }
    
    def _validate_question(self, question_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate a generated question to ensure it meets quality standards.
        
        Args:
            question_data: The question data to validate
            
        Returns:
            Tuple of (is_valid, reason)
        """
        question_type = question_data.get("type", "")
        question_text = question_data.get("question", "")
        
        # Check for empty or very short questions
        if not question_text or len(question_text) < 20:
            return False, "Question text is too short or empty"
        
        # Check for questions that are just fragments from the content
        if "______" in question_text and question_type == "multiple-choice":
            # Check if this is just a fill-in-the-blank with a single word
            if question_text.count("______") == 1 and "Complete the following" in question_text:
                return False, "Simple fill-in-the-blank questions are not educational enough"
        
        # Check for questions about superficial details (like author names)
        name_patterns = ["who wrote", "author", "who published", "wrote the", "created by"]
        if any(pattern in question_text.lower() for pattern in name_patterns):
            return False, "Questions about authorship are not substantive enough"
            
        # Check for date-focused questions
        date_patterns = ["what year", "when was", "which date", "was published in"]
        if any(pattern in question_text.lower() for pattern in date_patterns):
            return False, "Questions focused on dates are not substantive enough"
        
        # Multiple-choice specific validations
        if question_type == "multiple-choice":
            options = question_data.get("options", [])
            answer = question_data.get("answer", "")
            explanation = question_data.get("explanation", "")
            
            # Check if we have enough options
            if len(options) < 3:
                return False, "Multiple-choice question needs at least 3 options"
                
            # Check if answer is valid
            if not answer or (isinstance(answer, str) and answer not in "ABCD"):
                return False, "Multiple-choice answer must be one of A, B, C, D"
                
            # Check for options that are too similar or too different in length
            option_lengths = [len(str(opt)) for opt in options]
            avg_length = sum(option_lengths) / len(option_lengths)
            
            # If any option is too different in length from the average
            if any(abs(length - avg_length) > avg_length * 0.7 for length in option_lengths):
                return False, "Multiple-choice options should be similar in length"
                
            # Check for explanation
            if not explanation or len(explanation) < 30:
                return False, "Multiple-choice question needs a substantial explanation"
        
        # Free-text specific validations
        elif question_type == "free-text":
            answer = question_data.get("answer", "")
            key_points = question_data.get("key_points", [])
            
            # Check for model answer
            if not answer or len(answer) < 50:
                return False, "Free-text question needs a substantial model answer"
                
            # Check for key points
            if not key_points or len(key_points) < 2:
                return False, "Free-text question needs at least 2 key points"
        
        return True, "Question meets quality standards"
    
    def _fix_invalid_question(self, question_data: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """
        Attempt to fix invalid questions instead of discarding them.
        
        Args:
            question_data: The invalid question data
            reason: Why the question was invalid
            
        Returns:
            Fixed question data
        """
        question_type = question_data.get("type", "")
        
        # Handle common issues
        if "simple fill-in-the-blank" in reason:
            # Convert to a conceptual question
            if question_type == "multiple-choice" and "Complete the following" in question_data.get("question", ""):
                blank_sentence = question_data.get("question", "").replace("Complete the following sentence: ", "")
                concept = blank_sentence.replace("______", "concept")
                
                # Create a "what is" question about the concept
                question_data["question"] = f"Which of the following best describes the concept mentioned in this context: '{concept}'?"
                
                # Keep the same options and answer
        
        elif "options should be similar in length" in reason:
            # Try to equalize option lengths for multiple choice
            if question_type == "multiple-choice":
                options = question_data.get("options", [])
                if options:
                    # Find the average length
                    avg_length = sum(len(str(opt)) for opt in options) / len(options)
                    
                    # Expand short options and trim long ones
                    for i, option in enumerate(options):
                        if len(str(option)) < avg_length * 0.5:
                            # Expand short option
                            options[i] = f"{option} (as described in the text)"
                        elif len(str(option)) > avg_length * 1.5:
                            # Trim long option
                            words = str(option).split()
                            if len(words) > 8:
                                options[i] = " ".join(words[:8]) + "..."
                    
                    question_data["options"] = options
        
        elif "needs a substantial explanation" in reason:
            # Add generic explanation for multiple choice
            if question_type == "multiple-choice":
                answer_letter = question_data.get("answer", "")
                options = question_data.get("options", [])
                
                if answer_letter and options and 0 <= ord(answer_letter) - ord('A') < len(options):
                    answer_text = options[ord(answer_letter) - ord('A')]
                    question_data["explanation"] = f"The correct answer is {answer_letter}: {answer_text}. This option accurately reflects the information presented in the document. The other options either contradict this information or present incorrect interpretations of the content."
        
        elif "needs a substantial model answer" in reason:
            # Expand free-text answer
            if question_type == "free-text":
                question = question_data.get("question", "")
                key_points = question_data.get("key_points", [])
                
                # Generate a better answer from the question and key points
                better_answer = f"In response to the question about {question.lower().replace('?', '')}, several important aspects should be considered:\n\n"
                
                for i, point in enumerate(key_points):
                    better_answer += f"{i+1}. {point}.\n"
                
                better_answer += "\nConsidering these factors in depth provides a comprehensive understanding of the topic. Each element contributes to the overall analysis and helps establish a thorough framework for addressing the question."
                
                question_data["answer"] = better_answer
        
        elif "needs at least 2 key points" in reason:
            # Add generic key points for free-text
            if question_type == "free-text":
                question = question_data.get("question", "")
                
                # Generate generic key points based on question
                generic_points = [
                    "Clear definition of core concepts mentioned in the question",
                    "Thorough explanation with specific examples from the context",
                    "Critical analysis of implications or applications",
                    "Connections to broader themes or principles in the material"
                ]
                
                question_data["key_points"] = generic_points
        
        return question_data

    # Add this diagnostic function to QuestionGenerator class
    def debug_question_generation(self, topics: Optional[List[str]] = None, 
                                  question_type: str = "multiple-choice",
                                  difficulty: str = "medium") -> Dict[str, Any]:
        """
        Debug version of generate_question with detailed logging.
        """
        print("\n=== STARTING QUESTION GENERATION DEBUGGING ===")
        
        # Check topic
        topic = random.choice(topics) if topics and len(topics) > 0 else None
        print(f"Selected topic: {topic}")
        
        # Check context retrieval
        print("Retrieving contexts...")
        contexts = self.retrieval_system.retrieve_for_question_generation(
            topic=topic, 
            num_contexts=100
        )
        
        if not contexts:
            print("ERROR: No contexts retrieved. Check your vector store and retrieval system.")
            return self._generate_fallback_question(question_type)
        
        print(f"Successfully retrieved {len(contexts)} contexts")
        print(f"First context sample: {contexts[0]['content'][:100]}...")
        
        # Prepare context text
        context_text = "\n\n".join([ctx['content'] for ctx in contexts])
        print(f"Combined context length: {len(context_text)} characters")
        
        if self.ollama_available and self.use_ollama:
            print("\n=== Attempting Ollama generation ===")
            try:
                # Similar detailed steps for Ollama
                print(f"Using Ollama endpoint: {self.ollama_endpoint}")
                print(f"Using Ollama model: {self.ollama_model}")
                
                # Create prompt
                if question_type == "multiple-choice":
                    prompt = self._create_mc_prompt(context_text, difficulty, topic)
                else:
                    prompt = self._create_free_text_prompt(context_text, difficulty, topic)
                
                # Call Ollama...
                # Rest of debugging for Ollama
                pass
            except Exception as e:
                print(f"Error in Ollama generation: {str(e)}")
                print("Full traceback:")
                traceback.print_exc()
        else:
            print("\nSkipping Ollama (not available or disabled)")
        
        print("\n=== Falling back to simple question generation ===")
        question_data = self._generate_simple_question(context_text, question_type, difficulty)
        
        # Validate simple question
        is_valid, reason = self._validate_question(question_data)
        if is_valid:
            print("Simple question validation passed!")
        else:
            print(f"Simple question validation failed: {reason}")
            print("Attempting to fix...")
            question_data = self._fix_invalid_question(question_data, reason)
        
        print("\n=== QUESTION GENERATION DEBUGGING COMPLETE ===")
        return question_data