import re
from typing import Dict, Any, List, Optional

class IntentClassifier:
    """
    Classifies user input into different intent categories with high precision.
    This classifier focuses on reducing false positives and avoiding mixing intents.
    """
    def __init__(self):
        """Initialize the intent classifier with precise patterns for each intent type."""
        # Define contexts to disambiguate similar patterns
        self.contexts = {
            "review": [
                r'\breview\b', r'\bquiz\b', r'\btest\b', r'\bsession\b', 
                r'\bpractice\b', r'\bquestion\b', r'\bdifficulty\b'
            ],
            "speech": [
                r'\bspeech\b', r'\bvoice\b', r'\btalk\b', r'\blisten\b', 
                r'\bmicrophone\b', r'\bspeak\b', r'\brecognition\b'
            ],
            "document": [
                r'\bdocument\b', r'\bfile\b', r'\bpdf\b', r'\bpptx\b', 
                r'\bupload\b', r'\btext\b', r'\bmaterial\b'
            ],
            "settings": [
                r'\bsetting\b', r'\boption\b', r'\bconfigure\b', 
                r'\bpreferenc\b', r'\bcustom\b'
            ]
        }
        
        # Define intent patterns with word boundaries and more specific phrases
        self.patterns = {
            # Document-related intents
            "document_upload": [
                r'\b(upload|add|attach|send).{1,20}(document|pdf|file|pptx)\b',
                r'\b(document|pdf|file|pptx).{1,20}(upload|add|attach|send)\b',
                r'\bI.{1,10}(want|like|need).{1,20}(upload|add).{1,20}(document|pdf|file)\b'
            ],
            
            # Review session intents
            "start_review": [
                r'\b(start|begin|launch).{1,10}(review|quiz|test|practice|session)\b',
                r'\blet\'s (start|begin|do).{1,10}(review|quiz|test|practice)\b',
                r'\bI.{1,10}(want|like|ready).{1,10}(start|begin|do).{1,10}(review|quiz|test)\b'
            ],
            
            "stop_review": [
                r'\b(stop|end|finish|quit|exit|terminate).{1,10}(review|quiz|test|session|practice)\b',
                r'\b(cancel|halt).{1,10}(review|quiz|test|session|practice)\b'
            ],
            
            "review_status": [
                r'\b(what.{1,10}(status|progress)|how.{1,10}(doing|progressing))\b',
                r'\b(status|progress).{1,10}(review|quiz|test|session)\b',
                r'\bhow.{1,10}(am|are|is|was).{1,10}(doing|performing|scoring)\b',
                r'\b(correct|right|wrong|score|result).{1,10}(answer|question)\b'
            ],
            
            # Settings intents
            "review_settings": [
                r'\b(what|show|display|list).{1,15}(settings|options|configuration)\b',
                r'\b(what).{1,10}(is|are).{1,10}(current|available).{1,10}(settings|options)\b',
                r'\bcurrent.{1,10}(settings|options|configuration)\b',
                r'\bsettings.{1,10}(now|current|available)\b'
            ],
            
            "set_question_type": [
                r'\b(set|change|switch|use).{1,10}(question).{1,10}(type|style|format).{1,10}(to|as).{1,10}(multiple.?choice|free.?text|open.?ended)\b',
                r'\b(use|do|set).{1,10}(multiple.?choice|free.?text|open.?ended).{1,10}(question|format|style)\b',
                r'\b(multiple.?choice|free.?text|open.?ended).{1,10}(question|format|style)\b'
            ],
            
            # Improved set_num_questions patterns
            "set_num_questions": [
                r'\b(\d+)\s+questions?\b',  # Simple "10 questions"
                r'\bquestions?\s+(\d+)\b',  # "questions 10"
                r'\b(set|use|do|want|have|give|ask|make).{0,10}(\d+).{0,5}questions?\b',  # "set 10 questions"
                r'\b(set|change|make).{0,10}(number|amount|count).{0,10}questions?.{0,10}(\d+)\b',  # "set number of questions to 10"
                r'\bI.{0,10}(want|would like|need).{0,10}(\d+).{0,5}questions?\b',  # "I want 10 questions"
                r'\b(prepare|create|have|do).{0,5}(\d+).{0,5}questions?\b',  # "prepare 10 questions"
                r'\bquestions?.{0,5}(should|will).{0,5}be.{0,5}(\d+)\b'  # "questions should be 10"
            ],
            
            "set_topic": [
                r'\b(set|change|focus|concentrate).{1,10}(topic|subject).{1,10}(to|on|about)\b',
                r'\b(topic|subject).{1,5}(should|will|must).{1,5}(be|include)\b',
                r'\bfocus.{1,10}(on).{1,10}(topic|subject)\b'
            ],
            
            "set_difficulty": [
                r'\b(set|change|use).{1,10}(difficulty|level).{1,10}(to|as).{1,10}(easy|medium|hard|simple|intermediate|difficult|challenging)\b',
                r'\b(easy|medium|hard|simple|difficult|challenging).{1,10}(difficulty|level|questions)\b',
                r'\b(make|set).{1,10}(it|questions).{1,10}(easy|medium|hard|simple|difficult|challenging)\b'
            ],
            
            # Speech recognition intents - very specific to avoid confusion
            "enable_speech": [
                r'\b(enable|activate|turn.{1,5}on).{1,10}(speech|voice|microphone|speaking|recognition)\b',
                r'\b(use|start).{1,10}(speech|voice).{1,10}(recognition|input|mode)\b',
                r'\bI.{1,10}(want|like).{1,10}(speak|talk).{1,10}(to|with|instead).{1,10}(typing|text)\b'
            ],
            
            "disable_speech": [
                r'\b(disable|deactivate|turn.{1,5}off).{1,10}(speech|voice|microphone|speaking|recognition)\b',
                r'\b(stop|don\'t).{1,10}(use|listen).{1,10}(speech|voice|microphone)\b',
                r'\b(type|text).{1,10}(only|instead).{1,10}(speech|voice|talking)\b'
            ],

            "continue": [
                r'\b(next|continue|proceed|go on|go ahead|move on)\b',
                r'\b(next question|another question|ask another|ask next)\b',
                r'^(ok|okay|sure|yes|yep|yeah|y|alright|fine|ready|got it)\b'
            ],

            "out_of_scope": [
                r'\b(who|what|where|when|why|how).{1,30}(world|universe|life|economy|politics|news|weather)\b',
                r'\b(tell|explain|describe).{1,20}(yourself|history|science|math|physics|chemistry|biology)\b',
                r'\b(what).{1,5}(is|are).{1,20}(meaning|purpose|goal|objective).{1,10}(life|universe|existence)\b',
                r'\b(browse|search|find|google|look up|navigate).{1,20}(internet|web|online)\b',
                r'\b(write|create|generate).{1,20}(program|app|application|website|code).{1,20}(not|unrelated).{1,20}(document|study|review)\b',
                r'\b(analyze|process|examine).{1,20}(data|information|statistics).{1,20}(not|unrelated).{1,20}(document|study|review)\b'
            ],

            "unknown": [
                r'\b(help|assist|do something|not sure|confused|lost)\b',
                r'^(?!.*\b(review|document|speech|question|topic|difficulty|setting)\b).*\b(what|how|can you|would you|could you)\b.*$',
                r'^(?!.*\b(upload|start|stop|status|setting|question|topic|difficulty|speech)\b).*\b(do|work|function|capability)\b.*$'
            ]
        }
    
    def classify(self, text: str) -> Dict[str, Any]:
        """
        Classify text into intent types with high precision.
        
        Args:
            text: User input text
            
        Returns:
            Dictionary with primary intent type and associated data
        """
        # Determine the dominant context in the text
        context_scores = self._determine_context(text)
        dominant_context = max(context_scores.items(), key=lambda x: x[1])[0] if context_scores else None
        
        # Log for debugging
        print(f"Context scores: {context_scores}")
        print(f"Dominant context: {dominant_context}")
        
        # Initialize result with default intent as "answer"
        result = {
            "intent": "answer", 
            "answer": text,
            "text": text,
            "additional_intents": []
        }
        
        # Check for set_num_questions intent first (special handling)
        # This is a direct check for number patterns to catch simple cases
        num_questions_match = self._check_num_questions(text)
        if num_questions_match:
            result = {
                "intent": "set_num_questions",
                "num_questions": num_questions_match,
                "text": text,
                "additional_intents": []
            }
            print(f"Direct number match: {num_questions_match}")
            
            # Now look for other intents in the same message
            other_intents = self._find_other_intents(text, "set_num_questions")
            if other_intents:
                result["additional_intents"] = other_intents
            
            return result
        
        # Process multiple sentences for potential multiple intents
        sentences = self._split_into_sentences(text)
        detected_intents = []
        
        # Process each sentence
        for sentence in sentences:
            intent_match = self._match_intent(sentence, dominant_context)
            if intent_match:
                detected_intents.append(intent_match)
                print(f"Matched intent '{intent_match}' in sentence: '{sentence}'")
            else:
                print(f"No intent match for sentence: '{sentence}'")
        
        # If no intents were detected in sentences, check for out-of-scope or unknown intents
        if not detected_intents:
            # Check if the text matches out-of-scope patterns
            for pattern in self.patterns["out_of_scope"]:
                if re.search(pattern, text, re.IGNORECASE):
                    return {
                        "intent": "out_of_scope",
                        "text": text,
                        "additional_intents": []
                    }
            
            # Check if the text matches unknown intent patterns
            for pattern in self.patterns["unknown"]:
                if re.search(pattern, text, re.IGNORECASE):
                    return {
                        "intent": "unknown",
                        "text": text,
                        "additional_intents": []
                    }
            
            # If still no match, return the default answer intent
            return result
            
        # Process detected intents
        primary_intent = detected_intents[0]
        
        # Extract specific data from the intent
        primary_data = self._extract_intent_data(text, primary_intent)
        
        # Update the result with primary intent data
        result.update(primary_data)
        
        # Add additional intents, if any
        additional_intents = []
        for intent in detected_intents[1:]:
            if intent != primary_intent:  # Avoid duplicates
                intent_data = self._extract_intent_data(text, intent)
                additional_intents.append(intent_data)
        
        # Only include additional intents in the result if there are any
        if additional_intents:
            result["additional_intents"] = additional_intents
            
        return result
    
    def _check_num_questions(self, text: str) -> Optional[int]:
        """Direct check for number of questions pattern."""
        # Simple pattern to catch "X questions" or variations
        patterns = [
            r'\b(\d+)\s+questions?\b',  # "10 questions"
            r'\b(\d+)\s+q\b',  # "10 q"
            r'\bquestions?\s+(\d+)\b',  # "questions 10"
            r'\b(set|use|do|want|have).{1,10}(\d+).{1,5}questions?\b',  # "set 10 questions"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract the number from the match
                num_str = next((g for g in match.groups() if g and g.isdigit()), None)
                if num_str:
                    try:
                        return int(num_str)
                    except ValueError:
                        continue
        
        return None
    
    def _find_other_intents(self, text: str, exclude_intent: str) -> List[Dict[str, Any]]:
        """Find other intents in the text excluding a specified intent."""
        other_intents = []
        sentences = self._split_into_sentences(text)
        
        for sentence in sentences:
            for intent, patterns in self.patterns.items():
                if intent == exclude_intent:
                    continue
                    
                for pattern in patterns:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        intent_data = self._extract_intent_data(sentence, intent)
                        if not any(i["intent"] == intent for i in other_intents):
                            other_intents.append(intent_data)
                            break
        
        return other_intents
    
    def _determine_context(self, text: str) -> Dict[str, float]:
        """
        Determine the contextual domain of the text to aid in disambiguation.
        Returns a dictionary of context types and their scores.
        """
        context_scores = {context: 0 for context in self.contexts}
        
        for context_type, patterns in self.contexts.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                context_scores[context_type] += len(matches) * 2  # Weight direct matches
                
            # Look for related words or partial matches
            if context_type == "review" and re.search(r'\b(ask|question|quiz)\b', text, re.IGNORECASE):
                context_scores[context_type] += 1
            elif context_type == "speech" and re.search(r'\b(talk|hear|audio|sound)\b', text, re.IGNORECASE):
                context_scores[context_type] += 1
            elif context_type == "document" and re.search(r'\b(content|read|material|learn)\b', text, re.IGNORECASE):
                context_scores[context_type] += 1
            elif context_type == "settings" and re.search(r'\b(change|adjust|modify|set)\b', text, re.IGNORECASE):
                context_scores[context_type] += 1
         
        # Add context detection for out-of-scope queries
        out_of_scope_keywords = [
            r'\b(news|weather|sports|politics|economy|stock|crypto|bitcoin)\b',
            r'\b(meaning of life|universe|philosophy|religion|beliefs)\b',
            r'\b(tell me about yourself|who are you|how do you work|what can you do)\b',
            r'\b(search|find|browse|google|web|internet)\b'
        ]

        for pattern in out_of_scope_keywords:
            if re.search(pattern, text, re.IGNORECASE):
                # If we detect out-of-scope keywords, reduce the scores of other contexts
                for key in context_scores:
                    context_scores[key] -= 1
                break

        return context_scores
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for individual processing."""
        # Simple split on sentence-ending punctuation
        sentences = re.split(r'[.!?]\s+', text)
        # Remove empty sentences and strip whitespace
        return [s.strip() for s in sentences if s.strip()]
    
    def _match_intent(self, text: str, dominant_context: Optional[str] = None) -> Optional[str]:
        """
        Match text against intent patterns, using context to disambiguate.
        Returns the matched intent or None.
        """
        matched_intents = {}
        
        for intent, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    # If we have a match, associate it with this intent
                    if intent not in matched_intents:
                        matched_intents[intent] = 0
                    matched_intents[intent] += 1
        
        if not matched_intents:
            return None
            
        # If we have multiple matches, use context to disambiguate
        if len(matched_intents) > 1 and dominant_context:
            for intent in list(matched_intents.keys()):
                # Resolve ambiguity between start_review and enable_speech
                if intent == "start_review" and "enable_speech" in matched_intents:
                    # If the dominant context is speech, prefer speech-related intent
                    if dominant_context == "speech":
                        matched_intents.pop("start_review", None)
                    # If the dominant context is review, prefer review-related intent
                    elif dominant_context == "review":
                        matched_intents.pop("enable_speech", None)
        
        # Return the intent with the most matches
        if matched_intents:
            return max(matched_intents.items(), key=lambda x: x[1])[0]
        
        return None
    
    def _extract_intent_data(self, text: str, intent: str) -> Dict[str, Any]:
        """
        Extract relevant data for a specific intent.
        Returns a dictionary with intent and associated data.
        """
        result = {"intent": intent, "text": text}
        
        # Extract specific data based on intent type
        if intent == "set_question_type":
            if re.search(r'\b(multiple.?choice|mc)\b', text, re.IGNORECASE):
                result["question_type"] = "multiple-choice"
            elif re.search(r'\b(free.?text|open.?ended)\b', text, re.IGNORECASE):
                result["question_type"] = "free-text"
        
        elif intent == "set_num_questions":
            # Enhanced number extraction - try multiple patterns
            patterns = [
                r'(\d+)\s+questions?',  # "10 questions"
                r'questions?\s+(\d+)',  # "questions 10"
                r'(set|use|have|want|do).{1,15}(\d+).{1,5}questions?',  # "set 10 questions"
                r'questions?.{1,15}(be|is|to|as|at|of).{1,5}(\d+)',  # "questions to 10"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Find the first group that contains a digit
                    num_str = next((g for g in match.groups() if g and g.isdigit()), None)
                    if num_str:
                        try:
                            result["num_questions"] = int(num_str)
                            break
                        except ValueError:
                            continue
        
        elif intent == "set_difficulty":
            # Extract difficulty level
            if re.search(r'\b(easy|simple|beginner)\b', text, re.IGNORECASE):
                result["difficulty"] = "easy"
            elif re.search(r'\b(medium|moderate|intermediate)\b', text, re.IGNORECASE):
                result["difficulty"] = "medium"
            elif re.search(r'\b(hard|difficult|challenging|advanced)\b', text, re.IGNORECASE):
                result["difficulty"] = "hard"
        
        elif intent == "set_topic":
            # Advanced topic extraction logic for open domain
            # Pattern-based extraction with multiple approaches
            topics = []
            
            # Approach 1: Extract topics using structured patterns
            # Look for common constructs like "set topic to X" or "focus on topic X"
            structured_patterns = [
                # "set topic to X" or "set topic as X"
                r'(?:set|change|make).{1,5}(?:topic|subject).{1,5}(?:to|as|about|:)\s*([^,.!?;]+)',
                # "focus on X" where X is likely a topic
                r'focus\s+on\s+(?:topic|subject)?\s*:?\s*([^,.!?;]+)',
                # "topic should be X"
                r'(?:topic|subject).{1,5}(?:should|will|must|can).{1,5}(?:be|include|cover)\s*:?\s*([^,.!?;]+)',
                # Topics after a colon (e.g., "topics: X, Y, Z")
                r'(?:topic|subject|topics|subjects)\s*:\s*([^.!?;]+)',
                # Capturing topics after "about" or "regarding"
                r'(?:about|regarding|concerning)\s+(?:topic|subject)?\s*:?\s*([^,.!?;]+)'
            ]
            
            for pattern in structured_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    topic_text = match.group(1).strip()
                    # If multiple topics are separated by commas or "and"
                    if ',' in topic_text or ' and ' in topic_text:
                        # Split by comma and "and"
                        sub_topics = re.split(r',\s*|\s+and\s+', topic_text)
                        topics.extend([t.strip() for t in sub_topics if t.strip()])
                    else:
                        topics.append(topic_text)
            
            # If structured patterns didn't find anything, try a more aggressive approach
            if not topics:
                # Approach 2: Extract topics by looking at the content after known markers
                marker_words = ['topic', 'subject', 'focus', 'about', 'on']
                for marker in marker_words:
                    marker_positions = [m.start() for m in re.finditer(r'\b' + marker + r'\b', text.lower())]
                    for pos in marker_positions:
                        # Look at what comes after the marker word (up to the next punctuation or end)
                        remainder = text[pos + len(marker):].strip()
                        if remainder:
                            # Skip common connecting words
                            skip_words = ['to', 'on', 'be', 'is', 'are', 'should', 'will', 'can', 'must', 'the', 'a', 'an', 'of']
                            for skip in skip_words:
                                if remainder.lower().startswith(skip + ' '):
                                    remainder = remainder[len(skip):].strip()
                            
                            # Extract until end of sentence or punctuation
                            match = re.match(r'(?::|;|,)?\s*([^,.!?;]+)', remainder)
                            if match:
                                topic_text = match.group(1).strip()
                                if topic_text and not any(topic_text.lower() == t.lower() for t in topics):
                                    if ',' in topic_text or ' and ' in topic_text:
                                        sub_topics = re.split(r',\s*|\s+and\s+', topic_text)
                                        topics.extend([t.strip() for t in sub_topics if t.strip()])
                                    else:
                                        topics.append(topic_text)
            
            # Approach 3: Last resort - if we still don't have topics, look for keywords that might be topics
            if not topics:
                # Extract words that are likely to be topics (not in a stopword list)
                words = re.findall(r'\b[A-Za-z][A-Za-z0-9_-]{2,}\b', text)
                stopwords = ['set', 'topic', 'subject', 'focus', 'on', 'the', 'to', 'and', 'for', 'with',
                            'should', 'will', 'can', 'be', 'about', 'regarding', 'want', 'please',
                            'this', 'that', 'these', 'those', 'make', 'change', 'modify', 'create']
                
                for word in words:
                    if word.lower() not in stopwords and len(word) > 2:
                        # Check if this word appears after any of our marker words
                        for marker in marker_words:
                            marker_pattern = r'\b' + marker + r'\b.*?\b' + re.escape(word) + r'\b'
                            if re.search(marker_pattern, text, re.IGNORECASE):
                                topics.append(word)
                                break
            
            # Clean up topics
            clean_topics = []
            for topic in topics:
                # Remove any leading/trailing punctuation or whitespace
                clean_topic = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', topic).strip()
                # Remove common connector words at the beginning
                clean_topic = re.sub(r'^(the|a|an|is|are|be|to|of)\s+', '', clean_topic, flags=re.IGNORECASE).strip()
                
                if clean_topic and len(clean_topic) > 1:  # Avoid single letter topics
                    if not any(t.lower() == clean_topic.lower() for t in clean_topics):
                        clean_topics.append(clean_topic)
            
            # If we found topics, add them to the result
            if clean_topics:
                result["topics"] = clean_topics
            else:
                # If no topics were found, let the user know they need to specify in a clearer format
                result["topic_extraction_failed"] = True
        
        elif intent == "answer":
            result["answer"] = text

        elif intent == "out_of_scope":
            # For out of scope intent, we don't need to extract any specific data
            pass
            
        elif intent == "unknown":
            # For unknown intent, we don't need to extract any specific data
            pass
            
        return result