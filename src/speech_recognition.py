from streamlined_custom_component import create_component

def speech_recognition():
    """
    Create a custom speech recognition component using streamlined_custom_component.
    
    Returns:
        A component function to be called from the app
    """
    
    # Create the HTML/JS for the speech recognition component
    speech_html = """
    <html>
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600&display=swap" rel="stylesheet">
        
        <style>
          body, button, div {
              font-family: 'Source Sans Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
          }

          .speech-button {
              background-color: #8F001A;
              border: none;
              color: white;
              padding: 10px 15px;
              text-align: center;
              font-size: 16px;
              margin: 4px 0;
              cursor: pointer;
              border-radius: 10px; /* Elongated circle */
              width: 100%; /* Spans the full width */
              height: 45px;
              box-shadow: 0 2px 4px rgba(0,0,0,0.2);
              transition: all 0.3s ease;
              display: flex;
              align-items: center;
              justify-content: center;
          }
          
          .speech-button:hover {
              background-color: #a33449;
              box-shadow: 0 3px 6px rgba(0,0,0,0.2);
          }
          
          .speech-button.listening {
              background-color: #e61239;
              animation: pulse 1.5s infinite;
          }
          
          @keyframes pulse {
              0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.7); }
              70% { transform: scale(1.02); box-shadow: 0 0 0 8px rgba(244, 67, 54, 0); }
              100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(244, 67, 54, 0); }
          }
          
          .speech-container {
              display: flex;
              flex-direction: column;
              width: 100%;
              padding: 10px 0;
          }
          
          .speech-status {
              margin-top: 10px;
              font-size: 14px;
              color: #555;
              font-weight: 400;
              text-align: center;
          }

          .mic-icon {
              width: 20px;
              height: 20px;
              fill: white;
              margin-right: 8px;
          }
          
          .button-text {
              font-weight: 500;
          }
        </style>
      </head>
      <body>
        <div class="speech-container">
            <button id="mic-button" class="speech-button">
                <svg class="mic-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                </svg>
                <span class="button-text">Ready</span>
            </button>
            <div id="speech-status" class="speech-status">
                Click button or press Ctrl + Space
            </div>
        </div>

        <script>
          // Component communication functions
          function sendMessageToStreamlitClient(type, data) {
              var outData = Object.assign({
                  isStreamlitMessage: true,
                  type: type,
              }, data);
              window.parent.postMessage(outData, "*");
          }

          function init() {
              sendMessageToStreamlitClient("streamlit:componentReady", {apiVersion: 1});
          }

          function setFrameHeight(height) {
              sendMessageToStreamlitClient("streamlit:setFrameHeight", {height: height});
          }

          function sendDataToPython(data) {
              sendMessageToStreamlitClient("streamlit:setComponentValue", data);
          }

          // Speech Recognition Implementation
          const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
          let isListening = false;
          let finalTranscript = '';
          let recognition;
          
          // DOM elements
          const micButton = document.getElementById("mic-button");
          const statusElement = document.getElementById("speech-status");
          
          if (!SpeechRecognition) {
              statusElement.textContent = "Not supported in this browser";
              micButton.disabled = true;
              micButton.style.backgroundColor = "#ccc";
              
              // Send error to Python
              sendDataToPython({
                  value: {
                      status: "error",
                      error: "Speech recognition not supported"
                  },
                  dataType: "json",
              });
          } else {
              // Initialize recognition
              recognition = new SpeechRecognition();
              recognition.lang = 'en-US';
              recognition.interimResults = true;
              recognition.maxAlternatives = 1;
              
              // Recognition event handlers
              recognition.onstart = function() {
                  isListening = true;
                  statusElement.textContent = "";
                  micButton.classList.add("listening");
                  micButton.querySelector('.button-text').textContent = "Listening...";
                  finalTranscript = '';
                  
                  // Send status update to Python
                  sendDataToPython({
                      value: {
                          status: "listening",
                          transcript: ""
                      },
                      dataType: "json",
                  });
              };
              
              recognition.onresult = function(event) {
                  let interimTranscript = '';
                  
                  for (let i = event.resultIndex; i < event.results.length; ++i) {
                      if (event.results[i].isFinal) {
                          finalTranscript += event.results[i][0].transcript + ' ';
                      } else {
                          interimTranscript += event.results[i][0].transcript + ' ';
                      }
                  }
                  
                  // Update status with interim results
                  statusElement.textContent = "Recognized: " + interimTranscript;
                  
                  // Send interim results to Python
                  const currentTranscript = (finalTranscript + interimTranscript).trim();
                  sendDataToPython({
                      value: {
                          status: "interim",
                          transcript: currentTranscript
                      },
                      dataType: "json",
                  });
              };
              
              recognition.onerror = function(event) {
                  statusElement.textContent = "Error: " + event.error;
                  isListening = false;
                  micButton.classList.remove("listening");
                  micButton.querySelector('.button-text').textContent = "Speak Now";
                  
                  // Send error to Python
                  sendDataToPython({
                      value: {
                          status: "error",
                          error: event.error
                      },
                      dataType: "json",
                  });
              };
              
              recognition.onend = function() {
                  isListening = false;
                  micButton.classList.remove("listening");
                  micButton.querySelector('.button-text').textContent = "Ready";
                  
                  if (finalTranscript.trim()) {
                      statusElement.textContent = "Transcript ready";
                      
                      // Send final transcript to Python and mark it for processing
                      sendDataToPython({
                          value: {
                              status: "final",
                              transcript: finalTranscript.trim(),
                              process_immediately: true  // Flag to trigger immediate processing
                          },
                          dataType: "json",
                      });
                      
                      // Clear finalTranscript to prevent duplicates
                      finalTranscript = '';
                  } else {
                      statusElement.textContent = "Click button or press Ctrl + Space";
                      
                      // Send empty result to Python
                      sendDataToPython({
                          value: {
                              status: "ready",
                              transcript: ""
                          },
                          dataType: "json",
                      });
                  }
              };
              
              recognition.onnomatch = function() {
                  statusElement.textContent = "Didn't recognize that";
                  
                  // Send nomatch to Python
                  sendDataToPython({
                      value: {
                          status: "nomatch",
                          transcript: ""
                      },
                      dataType: "json",
                  });
                  
                  setTimeout(() => {
                      statusElement.textContent = "Click button or press Ctrl + Space";
                  }, 2000);
              };
                  
              // Button click handler
              micButton.addEventListener("click", toggleRecognition);
              
              // Keyboard shortcut (Ctrl+Space)
              document.addEventListener("keydown", function(event) {
                  if (event.ctrlKey && event.code === "Space") {
                      event.preventDefault();
                      toggleRecognition();
                  }
              });
              
              // Toggle recognition
              function toggleRecognition() {
                  if (isListening) {
                      recognition.stop();
                  } else {
                      try {
                          statusElement.textContent = "Starting...";
                          setTimeout(() => {
                              recognition.start();
                          }, 150);
                      } catch (error) {
                          statusElement.textContent = "Error starting";
                          sendDataToPython({
                              value: {
                                  status: "error",
                                  error: "Failed to start recognition"
                              },
                              dataType: "json",
                          });
                      }
                  }
              }
          }

          // Handle incoming data from Python
          function onDataFromPython(event) {
              if (event.data.type !== "streamlit:render") return;
              
              // We could handle configuration options here if needed
              // For example: event.data.args.config_option
          }

          window.addEventListener("message", onDataFromPython);
          init();

          // Set the frame height after the component fully loads
          window.addEventListener("load", function() {
              window.setTimeout(function() {
                  setFrameHeight(120);  // Set appropriate height
              }, 0);
          });
        </script>
      </body>
    </html>
    """
    
    # Create the component using the existing streamlined_custom_component module
    speech_component = create_component(
        full_html=speech_html, 
        component_name="speech_recognition_component"
    )
    
    return speech_component