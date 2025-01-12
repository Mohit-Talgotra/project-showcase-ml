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
        return result['text']
    
    def analyze_content(self, transcript, screenshots):
        print("Analyzing content...")
        prompt = f"""
        Create a product documentation based on this transcript and {len(screenshots)} screenshots:
        
        Transcript: {transcript}
        
        Generate a markdown document with:
        1. Product Overview
        2. Key Features
        3. Technical Details
        
        Make it professional and concise.
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
                body { max-width: 800px; margin: 0 auto; padding: 20px; font-family: Arial; }
                img { max-width: 100%; margin: 20px 0; }
            </style>
        </head>
        <body>
            {{ content }}
            {% for screenshot in screenshots %}
            <img src="{{ screenshot }}" alt="Product Screenshot">
            {% endfor %}
        </body>
        </html>
        """
        
        html_content = markdown.markdown(markdown_content)
        template = Template(html_template)
        return template.render(
            content=html_content,
            screenshots=screenshots
        )
    
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
