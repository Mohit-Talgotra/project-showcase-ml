import whisper
from groq import Groq
import markdown
from jinja2 import Template
import os
from dotenv import load_dotenv

load_dotenv()

class SimpleDocGenerator:
    def __init__(self, api_key):
        self.whisper_model = whisper.load_model("base")
        self.groq_client = Groq(api_key=api_key)
    
    def process_audio(self, audio_path):
        print("Transcribing audio...")
        result = self.whisper_model.transcribe(audio_path)
        print(result['text'])
        return result['text']
    
    def analyze_content(self, transcript, screenshots):
        print("Analyzing content...")
        prompt = f"""
        Create a product documentation based on this transcript and {len(screenshots)} screenshots.
        
        Transcript: {transcript}
        
        Generate a markdown document with the following sections:
        1. Product Overview
        2. Key Features (with specific places to insert screenshots)
        3. Technical Details
        
        Important formatting instructions:
        - Use '{{{{screenshot-1}}}}' to indicate where the first screenshot should be placed
        - Use '{{{{screenshot-2}}}}' for the second screenshot, and so on
        - Create meaningful section transitions
        - Include image captions that describe what each screenshot shows
        
        Make it professional and concise while integrating the screenshots naturally into the content. Also, look out for any weird punctuation like out of place brackets which shouldn't be there.
        """
        
        response = self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="mixtral-8x7b-32768",
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    def create_html(self, markdown_content, screenshots):
        print("Generating HTML...")
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Product Documentation</title>
            <style>
                :root {
                    --primary-color: #2c3e50;
                    --secondary-color: #3498db;
                    --background-color: #f9fafb;
                    --text-color: #333;
                }
                
                body {
                    max-width: 1000px;
                    margin: 0 auto;
                    padding: 40px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    line-height: 1.6;
                    background-color: var(--background-color);
                    color: var(--text-color);
                }
                
                h1, h2, h3 {
                    color: var(--primary-color);
                    margin-top: 2em;
                    margin-bottom: 1em;
                    border-bottom: 2px solid var(--secondary-color);
                    padding-bottom: 0.5em;
                }
                
                h1 { font-size: 2.5em; }
                h2 { font-size: 2em; }
                h3 { font-size: 1.5em; }
                
                .content-wrapper {
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 15px rgba(0, 0, 0, 0.1);
                }
                
                .screenshot-container {
                    margin: 30px 0;
                    text-align: center;
                }
                
                .screenshot {
                    max-width: 100%;
                    border-radius: 4px;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    transition: transform 0.3s ease;
                }
                
                .screenshot:hover {
                    transform: scale(1.02);
                }
                
                .caption {
                    margin-top: 10px;
                    font-style: italic;
                    color: #666;
                }
                
                p {
                    margin: 1em 0;
                    text-align: justify;
                }
                
                code {
                    background-color: #f7f9fa;
                    padding: 2px 5px;
                    border-radius: 3px;
                    font-family: 'Consolas', monospace;
                }
                
                @media (max-width: 768px) {
                    body {
                        padding: 20px;
                    }
                    
                    .content-wrapper {
                        padding: 20px;
                    }
                }
            </style>
        </head>
        <body>
            <div class="content-wrapper">
                {{ content }}
            </div>
        </body>
        </html>
        """
        
        # Replace screenshot placeholders with HTML
        html_content = markdown.markdown(markdown_content)
        for i, screenshot in enumerate(screenshots, 1):
            placeholder = f"{{screenshot-{i}}}"
            screenshot_html = f"""
            <div class="screenshot-container">
                <img class="screenshot" src="{screenshot}" alt="Product Screenshot {i}">
                <p class="caption">Figure {i}</p>
            </div>
            """
            html_content = html_content.replace(placeholder, screenshot_html)
        
        template = Template(html_template)
        return template.render(content=html_content)
    
    def generate(self, audio_path, screenshot_paths):
        transcript = self.process_audio(audio_path)
        markdown_content = self.analyze_content(transcript, screenshot_paths)
        
        html_content = self.create_html(markdown_content, screenshot_paths)
        
        with open("documentation.md", "w") as f:
            f.write(markdown_content)
        
        with open("documentation.html", "w") as f:
            f.write(html_content)
            
        print("Documentation generated successfully!")
        return "documentation.html", "documentation.md"



def main():
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API_KEY is not set in the environment variables")
    
    model = SimpleDocGenerator(api_key)

    audio_path = "example_audio_snapshots/audio.mp3"
    screenshots = ["example_audio_snapshots/shot1.png", "example_audio_snapshots/shot2.png"]
    
    html_path, md_path = model.generate(audio_path, screenshots)
    print(f"Generated files: {html_path}, {md_path}")

if __name__ == "__main__":
    main()
