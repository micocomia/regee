import re
from typing import Dict, Any, Tuple, List

class IntentClassifier:
    """
    Classifies user input into different intent categories.
    """
    def __init__(self):
        """Initialize the intent classifier with patterns for each intent type."""
        # Compile regex patterns for each intent
        self.patterns = {
            "document_upload": re.compile(r'upload|add|provide|document|pdf|powerpoint|pptx', re.IGNORECASE),
            
            "start_review": re.compile(r'start|begin|quiz|review|test|practice', re.IGNORECASE),
            
            "stop_review": re.compile(r'stop|end|finish|quit|exit|terminate', re.IGNORECASE),
            
            "review_status": re.compile(r'status|progress|score|how.+doing|right|wrong|correct', re.IGNORECASE),
            
            "set_question_type": re.compile(r'multiple.?choice|free.?text|open.?ended', re.IGNORECASE),
            
            "set_num_questions": re.compile(r'(\d+)\s+questions', re.IGNORECASE),
            
            "set_topic": re.compile(r'topic|focus|about|concentrate', re.IGNORECASE),
            
            "set_difficulty": re.compile(r'easy|medium|hard|difficult|simple|challenging', re.IGNORECASE),
            
            "enable_speech": re.compile(r'enable|start|activate|turn on|use\s+speech|voice', re.IGNORECASE),
            
            "disable_speech": re.compile(r'disable|stop|deactivate|turn off|don\'t use\s+speech', re.IGNORECASE),
        }
    
    def classify(self, text: str) -> Dict[str, Any]:
        """
        Classify text into an intent type with associated data.
        
        Args:
            text: User input text
            
        Returns:
            Dictionary with intent type and associated data
        """
        # Check for question type intent
        if self.patterns["set_question_type"].search(text):
            if re.search(r'multiple.?choice', text, re.IGNORECASE):
                return {
                    "intent": "set_question_type",
                    "question_type": "multiple-choice",
                    "text": text
                }
            elif re.search(r'free.?text|open.?ended', text, re.IGNORECASE):
                return {
                    "intent": "set_question_type",
                    "question_type": "free-text",
                    "text": text
                }
        
        # Check for number of questions intent
        num_questions_match = self.patterns["set_num_questions"].search(text)
        if num_questions_match:
            try:
                num = int(num_questions_match.group(1))
                return {
                    "intent": "set_num_questions",
                    "num_questions": num,
                    "text": text
                }
            except (ValueError, IndexError):
                pass
        
        # Check for difficulty intent
        if self.patterns["set_difficulty"].search(text):
            if re.search(r'easy|simple|beginner', text, re.IGNORECASE):
                return {
                    "intent": "set_difficulty",
                    "difficulty": "easy",
                    "text": text
                }
            elif re.search(r'medium|moderate|intermediate', text, re.IGNORECASE):
                return {
                    "intent": "set_difficulty",
                    "difficulty": "medium",
                    "text": text
                }
            elif re.search(r'hard|difficult|challenging|advanced', text, re.IGNORECASE):
                return {
                    "intent": "set_difficulty",
                    "difficulty": "hard",
                    "text": text
                }
        
        # Check for topic intent
        if self.patterns["set_topic"].search(text):
            # Extract potential topics (simple approach)
            words = text.split()
            # Filter out common words and get potential topics
            topics = [word for word in words if len(word) > 3 and word.lower() not in 
                     ['topic', 'focus', 'about', 'concentrate', 'the', 'and', 'that']]
            if topics:
                return {
                    "intent": "set_topic",
                    "topics": topics,
                    "text": text
                }
        
        # Check other intent types
        for intent_type, pattern in self.patterns.items():
            if pattern.search(text):
                # Skip already checked intents with special handling
                if intent_type in ["set_question_type", "set_num_questions", 
                                  "set_difficulty", "set_topic"]:
                    continue
                
                return {
                    "intent": intent_type,
                    "text": text
                }
        
        # Default to answer intent if no other intent is detected
        return {
            "intent": "answer",
            "answer": text,
            "text": text
        }

